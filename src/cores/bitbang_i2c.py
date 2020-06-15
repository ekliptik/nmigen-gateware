from textwrap import dedent

from nmigen import *

from cores.mmio_gpio import MmioGpio
from soc.soc_platform import SocPlatform


class BitbangI2c(Elaboratable):
    def __init__(self, pins):
        self.mmio_gpio = MmioGpio(pads=(pins.scl, pins.sda))

    def elaborate(self, platform: SocPlatform):
        def i2c_overlay_hook(platform, top_fragment: Fragment, sames):
            assert hasattr(top_fragment, "memorymap")
            memorymap = top_fragment.memorymap
            dat_addr = memorymap.find_recursive(self.mmio_gpio.dat)
            set_addr = memorymap.find_recursive(self.mmio_gpio.set)
            dirout_addr = memorymap.find_recursive(self.mmio_gpio.dirout)

            overlay_text = dedent("""
                /dts-v1/;
                /plugin/;
                
                / {{
                        fragment@0 {{
                                target = <&amba>;
                
                                __overlay__ {{
                                        sensor_i2c: i2c@0 {{
                                                compatible = "i2c-gpio";
                                                sda-gpios = <&mmio_gpio 1 6>;
                                                scl-gpios = <&mmio_gpio 0 6>;
                                                i2c-gpio,delay-us = <2>;        /* ~100 kHz */
                                                #address-cells = <1>;
                                                #size-cells = <0>;
                                        }};
                
                                        mmio_gpio: gpio-controller@40000000 {{
                                                compatible = "brcm,bcm6345-gpio";
                                                reg-names = "set", "dat", "dirout";
                                                reg = <0x{:x} 1>, <0x{:x} 1>, <0x{:x} 1>;
                
                                                #gpio-cells = <2>;
                                                gpio-controller;
                                        }};
                                }};
                        }};
                }};
            """.format(set_addr.address, dat_addr.address, dirout_addr.address))
            platform.add_file("i2c_overlay.dts", overlay_text.encode("utf-8"))
            platform.init_script += "rmdir /sys/kernel/config/device-tree/overlays/bitbang_i2c\n"
            platform.init_script += "sleep 2  # we let the fpga load the bitstream to not hang the cpu\n"
            platform.init_script += "mkdir -p /sys/kernel/config/device-tree/overlays/bitbang_i2c\n"
            platform.init_script += "dtc -O dtb -@ i2c_overlay.dts -o - > /sys/kernel/config/device-tree/overlays/bitbang_i2c/dtbo\n"

        platform.prepare_hooks.append(i2c_overlay_hook)

        m = Module()
        m.submodules.mmio_gpio = self.mmio_gpio
        return m