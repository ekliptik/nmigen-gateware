# A simple experiment that demonstrates basic CSR / SOC functionality

from nmigen import *
from nmigen.vendor.lattice_machxo_2_3l import LatticeMachXO2Platform

from cores.csr_bank import StatusSignal, ControlSignal
from cores.primitives.lattice_machxo2.clocking import Osc
from devices import Usb3PluginPlatform, MicroR2Platform, ZyboPlatform, BetaPlatform, HdmiDigitizerPlatform
from soc.cli import cli
from soc.platforms import ZynqSocPlatform
from soc.platforms.jtag.jtag_soc_platform import JTAGSocPlatform


class Top(Elaboratable):
    def __init__(self):
        self.counter = StatusSignal(32)
        self.test_reg = ControlSignal(32)

    def elaborate(self, platform):
        m = Module()

        if isinstance(platform, ZynqSocPlatform):
            platform.ps7.fck_domain(requested_frequency=100e6)
            m.d.sync += self.counter.eq(self.counter + 1)
        elif isinstance(platform, LatticeMachXO2Platform):
            osc = m.submodules.osc = Osc()
            m.d.sync += self.counter.eq(self.counter + 1)
        else:
            m.d.comb += self.counter.eq(42)  # we dont have a clock source so we cant count

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(Usb3PluginPlatform, MicroR2Platform, ZyboPlatform, BetaPlatform, HdmiDigitizerPlatform), possible_socs=(JTAGSocPlatform, ZynqSocPlatform)) as platform:
        pass
