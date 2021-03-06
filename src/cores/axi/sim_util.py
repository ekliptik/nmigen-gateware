from cores.axi.axi_endpoint import Response
from util.sim import wait_for


def write_to_axi_channel(channel, value):
    yield channel.value.eq(value)
    yield channel.valid.eq(1)
    yield from wait_for(channel.ready)
    yield channel.valid.eq(0)


def read_from_axi_channel(channel):
    yield from wait_for(channel.valid)
    yield channel.ready.eq(1)
    if hasattr(channel, "value"):
        result = (yield channel.value)
    else:
        result = None
    response = (yield channel.resp)
    yield
    yield channel.ready.eq(0)
    return result, response


def axil_read(axi, addr):
    yield from write_to_axi_channel(axi.read_address, addr)
    value, response = (yield from read_from_axi_channel(axi.read_data))
    assert Response.OKAY.value == response
    return value


def axil_write(axi, addr, data):
    yield from write_to_axi_channel(axi.write_address, addr)
    yield from write_to_axi_channel(axi.write_data, data)
    result, response = (yield from read_from_axi_channel(axi.write_response))
    assert Response.OKAY.value == response