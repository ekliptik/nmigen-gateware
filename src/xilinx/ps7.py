from collections import OrderedDict
from functools import lru_cache

from nmigen import *
from nmigen.build import Clock

from cores.axi import AxiInterface
from os.path import join, dirname

from cores.axi.full_to_lite import AxiFullToLiteBridge
from cores.axi.interconnect import AxiInterconnect
from xilinx.clocking import Bufg
from util.nmigen import max_error_freq
from xilinx.xilinx_blackbox import XilinxBlackbox


class Ps7Block(XilinxBlackbox):
    module = "PS7"

class Ps7(Ps7Block):
    def __init__(self, here_is_the_only_place_that_instanciates_ps7=False):
        assert here_is_the_only_place_that_instanciates_ps7
        super().__init__()
        self.m = Module()
        self.clock_constraints = OrderedDict()

    def _axi_slave_helper(self, axi, ps7_port):
        m = self.m
        m.d.comb += [ps7_port.araddr.eq(axi.read_address.value)]
        m.d.comb += [ps7_port.arvalid.eq(axi.read_address.valid)]
        m.d.comb += [ps7_port.arid.eq(axi.read_address.id)]
        m.d.comb += [ps7_port.arburst.eq(axi.read_address.burst_type)]
        m.d.comb += [ps7_port.arl.en.eq(axi.read_address.burst_len)]
        m.d.comb += [ps7_port.arsize.eq(axi.read_address.beat_size_bytes)]
        m.d.comb += [ps7_port.arprot.eq(axi.read_address.protection_type)]
        m.d.comb += [axi.read_address.ready.eq(ps7_port.arready)]

        m.d.comb += [axi.read_data.value.eq(ps7_port.rdata)]
        m.d.comb += [axi.read_data.resp.eq(ps7_port.rre.sp)]
        m.d.comb += [axi.read_data.valid.eq(ps7_port.rvalid)]
        m.d.comb += [axi.read_data.id.eq(ps7_port.rid)]
        m.d.comb += [axi.read_data.last.eq(ps7_port.rlast)]
        m.d.comb += [ps7_port.rre.ady.eq(axi.read_data.ready)]

        m.d.comb += [ps7_port.awaddr.eq(axi.write_address.value)]
        m.d.comb += [ps7_port.awvalid.eq(axi.write_address.valid)]
        m.d.comb += [ps7_port.awid.eq(axi.write_address.id)]
        m.d.comb += [ps7_port.awburst.eq(axi.write_address.burst_type)]
        m.d.comb += [ps7_port.awl.en.eq(axi.write_address.burst_len)]
        m.d.comb += [ps7_port.awsize.eq(axi.write_address.beat_size_bytes)]
        m.d.comb += [ps7_port.awprot.eq(axi.write_address.protection_type)]
        m.d.comb += [axi.write_address.ready.eq(ps7_port.awready)]

        m.d.comb += [ps7_port.wdata.eq(axi.write_data.value)]
        m.d.comb += [ps7_port.wvalid.eq(axi.write_data.valid)]
        m.d.comb += [ps7_port.wstrb.eq(axi.write_data.byte_strobe)]
        m.d.comb += [ps7_port.wid.eq(axi.write_data.id)]
        m.d.comb += [ps7_port.wlast.eq(axi.write_data.last)]
        m.d.comb += [axi.write_data.ready.eq(ps7_port.wready)]

        m.d.comb += [axi.write_response.resp.eq(ps7_port.bre.sp)]
        m.d.comb += [axi.write_response.valid.eq(ps7_port.bvalid)]
        m.d.comb += [axi.write_response.id.eq(ps7_port.bid)]
        m.d.comb += [ps7_port.bre.ady.eq(axi.write_response.ready)]

    def _axi_master_helper(self, axi, ps7_port):
        m = self.m
        m.d.comb += [axi.read_address.value.eq(ps7_port.araddr)]
        m.d.comb += [axi.read_address.valid.eq(ps7_port.arvalid)]
        m.d.comb += [axi.read_address.id.eq(ps7_port.arid)]
        m.d.comb += [axi.read_address.burst_type.eq(ps7_port.arburst)]
        m.d.comb += [axi.read_address.burst_len.eq(ps7_port.arl.en)]
        m.d.comb += [axi.read_address.beat_size_bytes.eq(ps7_port.arsize)]
        m.d.comb += [axi.read_address.protection_type.eq(ps7_port.arprot)]
        m.d.comb += [ps7_port.arready.eq(axi.read_address.ready)]

        m.d.comb += [ps7_port.rdata.eq(axi.read_data.value)]
        m.d.comb += [ps7_port.rre.sp.eq(axi.read_data.resp)]
        m.d.comb += [ps7_port.rvalid.eq(axi.read_data.valid)]
        m.d.comb += [ps7_port.rid.eq(axi.read_data.id)]
        m.d.comb += [ps7_port.rlast.eq(axi.read_data.last)]
        m.d.comb += [axi.read_data.ready.eq(ps7_port.rre.ady)]

        m.d.comb += [axi.write_address.value.eq(ps7_port.awaddr)]
        m.d.comb += [axi.write_address.valid.eq(ps7_port.awvalid)]
        m.d.comb += [axi.write_address.id.eq(ps7_port.awid)]
        m.d.comb += [axi.write_address.burst_type.eq(ps7_port.awburst)]
        m.d.comb += [axi.write_address.burst_len.eq(ps7_port.awl.en)]
        m.d.comb += [axi.write_address.beat_size_bytes.eq(ps7_port.awsize)]
        m.d.comb += [axi.write_address.protection_type.eq(ps7_port.awprot)]
        m.d.comb += [ps7_port.awready.eq(axi.write_address.ready)]

        m.d.comb += [axi.write_data.value.eq(ps7_port.wdata)]
        m.d.comb += [axi.write_data.valid.eq(ps7_port.wvalid)]
        m.d.comb += [axi.write_data.byte_strobe.eq(ps7_port.wstrb)]
        m.d.comb += [axi.write_data.id.eq(ps7_port.wid)]
        m.d.comb += [axi.write_data.last.eq(ps7_port.wlast)]
        m.d.comb += [ps7_port.wready.eq(axi.write_data.ready)]

        m.d.comb += [ps7_port.bre.sp.eq(axi.write_response.resp)]
        m.d.comb += [ps7_port.bvalid.eq(axi.write_response.valid)]
        m.d.comb += [ps7_port.bid.eq(axi.write_response.id)]
        m.d.comb += [axi.write_response.ready.eq(ps7_port.bre.ady)]

    def get_axi_gp_master(self, number, clk) -> AxiInterface:
        axi = AxiInterface(addr_bits=32, data_bits=32, lite=False, id_bits=12, master=True)

        ps7_port = self.maxigp[number]
        self.m.d.comb += ps7_port.aclk.eq(clk)
        self._axi_master_helper(axi, ps7_port)

        return axi

    def get_axi_hp_slave(self, number, clk) -> AxiInterface:
        axi = AxiInterface(addr_bits=32, data_bits=64, lite=False, id_bits=12, master=False)

        ps7_port = self.saxi.hp[number]
        self.m.d.comb += ps7_port.aclk.eq(clk)
        self._axi_slave_helper(axi, ps7_port)

        return axi

    interconnect: AxiInterconnect = None

    def get_axi_lite_port(self):
        m = self.m
        if not self.interconnect:
            self.fck_domain(100e6, domain_name="axi_lite")
            axi_full_port: AxiInterface = self.get_axi_gp_master(0, ClockSignal("axi_lite"))
            axi_lite_bridge = m.submodules.axi_lite_bridge = DomainRenamer("axi_lite")(
                AxiFullToLiteBridge(axi_full_port)
            )
            self.interconnect = m.submodules.interconnect = DomainRenamer("axi_lite")(
                AxiInterconnect(axi_lite_bridge.lite_master)
            )
        return self.interconnect.get_port()

    @staticmethod
    @lru_cache()
    def get_possible_fclk_frequencies():
        with open(join(dirname(__file__), "ps7_fclk_frequencies.txt")) as f:
            return [int(x) for x in f.readlines()]

    def fck_domain(self, requested_frequency=100e6, domain_name="sync", max_error_percent=1) -> Clock:
        """
        Creates a clockdomain driven by a PS7 fclk
        :param max_error_percent:
        :param domain_name: teh name of the domain to create
        :param requested_frequency: the requested frequency
        :return: the real freqency that will be generated by the fclk
        """
        self.m.domains += ClockDomain(domain_name)
        fclk_num = len(self.clock_constraints)

        driving_signal = Signal(attrs={"KEEP": "TRUE"}, name="{}_driving_signal".format(domain_name))
        self.m.d.comb += driving_signal.eq(self.fclk.clk[fclk_num])

        bufg = self.m.submodules["fclk_bufg_{}".format(fclk_num)] = Bufg(driving_signal)

        real_freq = [x for x in self.get_possible_fclk_frequencies() if x <= requested_frequency][-1]
        max_error_freq(real_freq, requested_frequency, max_error_percent)
        self.clock_constraints[fclk_num] = (driving_signal, bufg.o, real_freq, domain_name)
        return Clock(real_freq)

    def elaborate(self, platform):
        m = Module()

        m.submodules.ps7_block = super().elaborate(platform)
        m.submodules.connections = self.m

        for i, (clock_signal, bufg_out, frequency, domain_name) in self.clock_constraints.items():
            if hasattr(platform, "add_clock_constraint"):
                self.m.d.comb += ClockSignal(domain_name).eq(bufg_out)
                platform.add_clock_constraint(clock_signal, frequency)
            else:  # we are a sim platform
                platform.add_sim_clock(domain_name, frequency)

        if hasattr(platform, "init_script"):
            platform.init_script += "\n".join(
                "# clockdomain '{name}':\n"
                "echo 1 > /sys/class/fclk/fclk{i}/enable\n"
                "echo {freq} > /sys/class/fclk/fclk{i}/set_rate\n"
                    .format(freq=int(freq), i=i, name=domain_name)
                for i, (clock_signal, bufg_out, freq, domain_name) in self.clock_constraints.items()
            )

        return m
