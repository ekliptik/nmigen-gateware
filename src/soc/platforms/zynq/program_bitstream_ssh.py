import subprocess
from shlex import quote

from nmigen.build.run import BuildProducts

default_host = "10.42.0.112"
default_user = "operator"
default_password = "axiom"


def run_on_zynq(cmd, host=default_host, user=default_user, password=default_password, sudo=False, sshpass=True):
    if sudo:
        cmd = "echo {} | sudo -S bash -c {}".format(password, quote(cmd))
    ssh_cmd = "ssh {}@{} {}".format(user, host, quote(cmd))
    if sshpass:
        ssh_cmd = "sshpass -p{} {}".format(password, ssh_cmd)
    print("\nexecuting: ", ssh_cmd)
    return subprocess.check_output(ssh_cmd, shell=True)


def copy_to_zynq(source, destination, host=default_host, user=default_user, password=default_password, sshpass=True):
    scp_cmd = "scp {} {}".format(quote(source), quote("{}@{}:{}".format(user, host, destination)))
    if sshpass:
        scp_cmd = "sshpass -p{} {}".format(password, scp_cmd)
    print("\nexecuting: ", scp_cmd)
    return subprocess.check_output(scp_cmd, shell=True)


def program_bitstream_ssh(platform, build_products: BuildProducts, name, **kwargs):
    fatbitstream_name = "{}.fatbitstream.sh".format(name)
    with build_products.extract(fatbitstream_name) as fatbitstream_file:
        copy_to_zynq(fatbitstream_file, "~/{}".format(fatbitstream_name))
    run_on_zynq("chmod +x {}".format(fatbitstream_name))
    run_on_zynq("./{}".format(fatbitstream_name), sudo=True)
