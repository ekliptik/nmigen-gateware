import unittest

from cores.axi.axi_endpoint import AxiEndpoint
from util.sim import SimPlatform
from cores.csr_bank.csr_bank import CsrBank, ControlSignal
from soc.platforms.zynq import ZynqSocPlatform
from util.sim import do_nothing
from cores.axi.sim_util import axil_read, axil_write


class TestAxiSlave(unittest.TestCase):
    def test_csr_bank(self, num_csr=10, testdata=0x12345678):
        platform = ZynqSocPlatform(SimPlatform())
        csr_bank = CsrBank()
        for i in range(num_csr):
            csr_bank.reg("csr#{}".format(i), ControlSignal(32))

        def testbench():
            axi = platform.axi_lite_master
            for addr in [0x4000_0000 + (i * 4) for i in range(num_csr)]:
                yield from axil_read(axi, addr)
                yield from axil_write(axi, addr, testdata)
                self.assertEqual(testdata, (yield from axil_read(axi, addr)))

        platform.sim(csr_bank, (testbench, "axi_lite"))

    def test_simple_test_csr_bank(self):
        platform = ZynqSocPlatform(SimPlatform())
        csr_bank = CsrBank()
        csr_bank.reg("csr", ControlSignal(32))

        def testbench():
            axi: AxiEndpoint = platform.axi_lite_master
            yield axi.read_address.value.eq(0x4000_0000)
            yield axi.read_address.valid.eq(1)
            yield from do_nothing()

        platform.sim(csr_bank, (testbench, "axi_lite"))
