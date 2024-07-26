import pytest
import logging

from .voq_helpers import get_eos_mac
from tests.common.helpers.parallel import parallel_run, reset_ansible_local_tmp
from tests.qos.args.qos_sai_args import add_qos_sai_args
from tests.qos.args.buffer_args import add_dynamic_buffer_calculation_args
from tests.common.helpers.dut_utils import get_host_visible_vars
from tests.common.utilities import get_inventory_files

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    '''
        Adds option to QoS pytest

        Args:
            parser: pytest parser object

        Returns:
            None
    '''
    add_qos_sai_args(parser)
    add_dynamic_buffer_calculation_args(parser)


@pytest.fixture(scope="module", autouse=True)
def chassis_facts(duthosts, request):
    """
    Fixture to add some items to host facts from inventory file.
    """
    for a_host in duthosts.nodes:

        if len(duthosts.supervisor_nodes) > 0:
            inv_files = get_inventory_files(request)
            host_vars = get_host_visible_vars(inv_files, a_host.hostname)
            assert 'slot_num' in host_vars, "Variable 'slot_num' not found in inventory for host {}"\
                .format(a_host.hostname)
            slot_num = host_vars['slot_num']
            a_host.facts['slot_num'] = int(slot_num[len("slot"):])


@pytest.fixture(scope="module")
def all_cfg_facts(duthosts):
    # { 'ixr_vdk_boar10' : [ asic0_results, asic1_results ] }
    #   asic0_results['ansible_facts']
    # result = duthosts.config_facts(source='persistent', asic_index='all')
    # return result
    # Working around issue 3020
    results = {}
    for node in duthosts.nodes:
        results[node.hostname] = node.config_facts(source='persistent', asic_index='all')
    return results


@reset_ansible_local_tmp
def _get_nbr_macs(nbrhosts, node=None, results=None):
    vm = nbrhosts[node]
    node_results = {}

    for intf in list(vm['conf']['interfaces'].keys()):
        logger.info("Get MAC on vm %s for intf: %s", node, intf)
        mac = get_eos_mac(vm, intf)
        logger.info("Found MAC on vm %s for intf: %s, mac: %s", node, intf, mac['mac'])
        node_results[intf] = mac['mac']

    results[node] = node_results


@pytest.fixture(scope="module")
def nbr_macs(nbrhosts):
    """
    Fixture to get all the neighbor mac addresses in parallel.

    Args:
        nbrhosts:

    Returns:
        Dictionary of MAC addresses of neighbor VMS, dict[vm_name][interface_name] = "mac address"

    """
    logger.debug("Get MACS for all neighbor hosts.")
    results = parallel_run(_get_nbr_macs, [nbrhosts], {}, list(nbrhosts.keys()), timeout=120)

    # result is DictProxy. Iterate it by using keys().
    for res in list(results.keys()):
        logger.info("parallel_results %s = %s", res, results[res])

    return results
