from nmigen import *

from .axi_endpoint import AxiEndpoint, BurstType
from cores.csr_bank import StatusSignal
from util.nmigen_misc import nMax, mul_by_pot
from ..ring_buffer_address_storage import RingBufferAddressStorage
from ..stream.fifo import SyncStreamFifo
from util.stream import StreamEndpoint


class AddressGenerator(Elaboratable):
    def __init__(self, ringbuffer: RingBufferAddressStorage, addr_bits, max_incr):
        self.base_addrs = ringbuffer.buffer_base_list
        self.max_buffer_size = ringbuffer.buffer_size
        self.current_buffer = ringbuffer.current_write_buffer

        # this is pessimistic but we rather allocate larger buffers and _really_ not write anywhere else
        self.max_addrs = Array(addr_base + self.max_buffer_size - (2 * max_incr) for addr_base in self.base_addrs)

        self.request = Signal()  # in
        self.inc = Signal(range(max_incr + 1))
        self.change_buffer = Signal()  # in
        self.addr = Signal(addr_bits, reset=self.base_addrs[0])  # out

        self.valid = Signal(reset=1)  # out
        self.done = Signal()  # in

    def elaborate(self, platform):
        m = Module()

        with m.If(~self.valid):
            with m.If(self.change_buffer):
                with m.If(self.current_buffer < len(self.base_addrs) - 1):
                    m.d.sync += self.current_buffer.eq(self.current_buffer + 1)
                    m.d.sync += self.addr.eq(self.base_addrs[self.current_buffer + 1])
                with m.Else():
                    m.d.sync += self.current_buffer.eq(0)
                    m.d.sync += self.addr.eq(self.base_addrs[0])
                m.d.sync += self.valid.eq(1)
            with m.Elif(self.request & (self.addr <= self.max_addrs[self.current_buffer])):
                m.d.sync += self.addr.eq(self.addr + self.inc)
                m.d.sync += self.valid.eq(1)

        with m.If(self.done):
            m.d.sync += self.valid.eq(0)

        return m


class AxiBufferWriter(Elaboratable):
    def __init__(
            self,
            ringbuffer: RingBufferAddressStorage,
            stream_source: StreamEndpoint,
            axi_slave=None,
            fifo_depth=32, max_burst_length=16
    ):
        self.ringbuffer = ringbuffer
        self.current_buffer = ringbuffer.current_write_buffer

        assert stream_source.is_sink is False
        assert stream_source.has_last
        self.stream_source = stream_source

        self.axi_slave = axi_slave

        self.fifo_depth = fifo_depth
        self.max_burst_length = max_burst_length

        self.error = StatusSignal()
        self.state = StatusSignal(32)
        self.burst_position = StatusSignal(range(self.max_burst_length))
        self.words_written = StatusSignal(32)
        self.buffers_written = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        if self.axi_slave is not None:
            assert not self.axi_slave.is_lite
            assert not self.axi_slave.is_master
            axi_slave = self.axi_slave
        else:
            clock_signal = Signal()
            m.d.comb += clock_signal.eq(ClockSignal())
            axi_slave = platform.ps7.get_axi_hp_slave(clock_signal)
        axi = AxiEndpoint.like(axi_slave, master=True)
        m.d.comb += axi.connect_slave(axi_slave)

        address_generator = m.submodules.address_generator = AddressGenerator(
            self.ringbuffer, axi.addr_bits, max_incr=self.max_burst_length * axi.data_bytes
        )

        data_fifo = m.submodules.data_fifo = SyncStreamFifo(self.stream_source, depth=self.fifo_depth, buffered=False)
        data = StreamEndpoint.like(data_fifo.output, is_sink=True, name="data_sink")
        m.d.comb += data.connect(data_fifo.output)

        assert len(data.payload) <= axi.data_bits

        # we do not currently care about the write responses
        m.d.comb += axi.write_response.ready.eq(1)

        current_burst_length_minus_one = Signal(range(self.max_burst_length))
        with m.FSM():
            def idle_state():
                # having the idle state in a function is a hack to be able to duplicate its logic
                m.d.comb += self.state.eq(0)
                m.d.sync += self.burst_position.eq(0)
                m.d.comb += address_generator.request.eq(1)
                with m.If(address_generator.valid & data.valid):
                    # we are doing a full transaction
                    next_burst_length = Signal(range(self.max_burst_length + 1))
                    m.d.comb += next_burst_length.eq(nMax(data_fifo.r_level, self.max_burst_length))
                    m.d.sync += current_burst_length_minus_one.eq(next_burst_length - 1)
                    m.d.sync += address_generator.inc.eq(mul_by_pot(next_burst_length, axi.data_bytes))
                    m.next = "ADDRESS"

            with m.State("IDLE"):
                idle_state()

            with m.State("ADDRESS"):
                m.d.comb += self.state.eq(1)
                m.d.comb += axi.write_address.value.eq(address_generator.addr)
                m.d.comb += axi.write_address.burst_len.eq(current_burst_length_minus_one)
                m.d.comb += axi.write_address.burst_type.eq(BurstType.INCR)
                m.d.comb += axi.write_address.valid.eq(1)
                with m.If(axi.write_address.ready):
                    m.next = "TRANSFER_DATA"
                    m.d.comb += data.ready.eq(1)
                    m.d.comb += address_generator.done.eq(1)

            def last_logic():
                # shared between TRANSFER_DATA and FLUSH
                with m.If(self.burst_position == current_burst_length_minus_one):
                    m.d.comb += axi.write_data.last.eq(1)
                    m.next = "IDLE"
                    idle_state()

            with m.State("TRANSFER_DATA"):
                m.d.comb += self.state.eq(2)

                with m.If(data.last):
                    m.d.sync += self.buffers_written.eq(self.buffers_written + 1)
                    m.d.comb += address_generator.change_buffer.eq(1)
                    m.next = "FLUSH"

                m.d.comb += axi.write_data.value.eq(data.payload)
                m.d.comb += axi.write_data.valid.eq(1)

                with m.If(axi.write_data.ready):
                    m.d.sync += self.words_written.eq(self.words_written + 1)
                    m.d.sync += self.burst_position.eq(self.burst_position + 1)
                    with m.If((self.burst_position < current_burst_length_minus_one) & ~data.last):
                        m.d.comb += data.ready.eq(1)
                        with m.If((~data.valid)):
                            # we have checked this earlier so this should never be a problem
                            m.d.sync += self.error.eq(1)
                last_logic()
            with m.State("FLUSH"):
                m.d.comb += axi.write_data.byte_strobe.eq(0)
                m.d.comb += axi.write_data.valid.eq(1)
                with m.If(axi.write_data.ready):
                    m.d.sync += self.words_written.eq(self.words_written + 1)
                    m.d.sync += self.burst_position.eq(self.burst_position + 1)
                last_logic()

        return m
