from nmigen import *

from cores.blink_debug import BlinkDebug
from cores.jtag.jtag import JTAG
from soc.memorymap import MemoryMap


class JTAGPeripheralConnector(Elaboratable):
    def __init__(self, peripheral):
        """
        A simple `PeripheralConnector` implementation for querying `Peripheral`s via JTAG in debug situations.
        This code does not handle memorymap stuff. Use in combination with PeripheralsAggregator
        """

        assert callable(peripheral.handle_read) and callable(peripheral.handle_write)
        assert isinstance(peripheral.range, range)
        self.peripheral = peripheral

    def elaborate(self, platform):
        m = Module()
        jtag = m.submodules.jtag = JTAG()
        led = Signal()  # platform.request("led", 0)
        led_debug = m.submodules.led_debug = DomainRenamer("wclk_in")(BlinkDebug(led, divider=22, max_value=8))
        m.submodules.in_jtag_domain = DomainRenamer("jtag")(self.elaborate_jtag_domain(platform, jtag, led_debug.value))
        return m

    def elaborate_jtag_domain(self, platform, jtag, led_debug):
        m = Module()

        write = Signal()
        addr = Signal(32)
        data = Signal(32)
        status = Signal()

        read_write_done = Signal()

        def read_write_done_callback(error):
            m.d.sync += status.eq(error)
            m.d.sync += read_write_done.eq(1)

        m.domains += ClockDomain("jtag_fsm")
        m.d.comb += ClockSignal("jtag_fsm").eq(ClockSignal())
        m.d.comb += ResetSignal("jtag_fsm").eq(jtag.reset)
        with m.FSM(domain="jtag_fsm"):
            def next_on_jtag_shift(next_state):
                with m.If(jtag.shift):
                    m.next = next_state

            with m.State("CMD"):  # we recive one bit that indicates if we want to read (0) or write (1)
                m.d.comb += led_debug.eq(0)
                m.d.sync += write.eq(jtag.tdi)
                next_on_jtag_shift("ADDR0")

            # address states
            for i in range(32):
                with m.State("ADDR{}".format(i)):
                    m.d.comb += led_debug.eq(1)
                    m.d.sync += addr[i].eq(jtag.tdi)
                    if i < 31:
                        next_on_jtag_shift("ADDR{}".format(i + 1))
                    else:
                        with m.If(write):
                            next_on_jtag_shift("WRITE0")
                        with m.Else():
                            next_on_jtag_shift("READ_WAIT")

            # read states
            with m.State("READ_WAIT"):
                m.d.comb += led_debug.eq(2)
                self.peripheral.handle_read(m, addr, data, read_write_done_callback)
                with m.If(read_write_done):
                    m.d.comb += jtag.tdo.eq(1)
                    next_on_jtag_shift("READ0")
            for i in range(32):
                with m.State("READ{}".format(i)):
                    m.d.comb += led_debug.eq(3)
                    m.d.comb += jtag.tdo.eq(data[i])
                    if i < 31:
                        next_on_jtag_shift("READ{}".format(i + 1))
                    else:
                        next_on_jtag_shift("READ_STATUS")
            with m.State("READ_STATUS"):
                m.d.comb += led_debug.eq(6)
                m.d.comb += jtag.tdo.eq(status)
                next_on_jtag_shift("CMD")

            # write states
            for i in range(32):
                with m.State("WRITE{}".format(i)):
                    m.d.comb += led_debug.eq(4)
                    m.d.sync += data[i].eq(jtag.tdi)
                    if i < 31:
                        next_on_jtag_shift("WRITE{}".format(i + 1))
                    else:
                        next_on_jtag_shift("WRITE_WAIT")
            with m.State("WRITE_WAIT"):
                m.d.comb += led_debug.eq(5)
                self.peripheral.handle_write(m, addr, data, read_write_done_callback)
                with m.If(read_write_done):
                    m.d.comb += jtag.tdo.eq(1)
                    next_on_jtag_shift("WRITE_STATUS")
            with m.State("WRITE_STATUS"):
                m.d.comb += led_debug.eq(6)
                m.d.comb += jtag.tdo.eq(status)
                next_on_jtag_shift("CMD")

        return m