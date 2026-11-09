from pathlib import Path
import json

from qiskit import QuantumCircuit

from tools.qusbt.QuSBT.main import qusbt_run

import subprocess, sys

"""
the following commands set the R that rpy2 uses, for each session
for instance, after restarting the command line, we would need to repeat the execution of these commands

export R_HOME="$(R RHOME)"
export RPY2_CFFI_MODE=ABI
"""

QUSBT_PATH = Path("tools/qusbt")
CONFIG_QUSBT = Path(QUSBT_PATH, "config_qusbt.json")

def translate_ps(ps_path, num_qubits, meas_qubits):
    with open(ps_path, "r") as f:
        ps_file = json.load(f)  

    ps_str = "[program_specification]\n"
    for in_st, prob_dist in ps_file.items():
        meas_prob = {}
        for val, prob in prob_dist.items():
            val_str=""
            for i in meas_qubits:
                val_str+=str(val[i-(num_qubits-1)])
                meas_prob[val_str] = meas_prob.get(val_str,0) + prob

        for val, prob in meas_prob.items():
            if (len(str(val)))==len(meas_qubits):
                ps_str += f"{in_st},{val}={prob}\n"

    return ps_str

def program_part(input_circuit_path, num_qubits, meas_qubits):
    qubits = ",".join(str(i) for i in range(num_qubits))
    meas_qubits=",".join(str(i) for i in meas_qubits)

    res = f"[program]\nroot={input_circuit_path}\nnum_qubit={num_qubits}\ninputID={qubits}\noutputID={meas_qubits}"

    return res

def qusbt_config_part():
    with open(CONFIG_QUSBT, "r") as f:
        qusbt_config = json.load(f)

    beta = qusbt_config["qusbt_configuration"]["beta"]
    conf_lvl = qusbt_config["qusbt_configuration"]["confidence_level"]
    str1 = f"[qusbt_configuration]\nbeta={beta}\nconfidence_level={conf_lvl}"

    pop_size = qusbt_config["GA_parameter"]["population_size"]
    off_pop_size = qusbt_config["GA_parameter"]["offspring_population_size"]
    max_eval = qusbt_config["GA_parameter"]["max_evaluations"]
    mut_prob = qusbt_config["GA_parameter"]["mutation_probability"]
    mut_dist_ind = qusbt_config["GA_parameter"]["mutation_distribution_index"]
    cross_prob = qusbt_config["GA_parameter"]["crossover_probability"]
    cross_dist_ind = qusbt_config["GA_parameter"]["crossover_distribution_index"]

    str2 = f"\n\n[GA_parameter]\npopulation_size={pop_size}\noffspring_population_size={off_pop_size}\nmax_evaluations={max_eval}"
    if mut_prob is not None:
        str2 + f"\nmutation_probability={mut_prob}"
    if mut_dist_ind is not None:
        str2 + f"\nmutation_distribution_index={mut_dist_ind}"
    if cross_prob is not None:
        str2 + f"\ncrossover_probability={cross_prob}"
    if cross_dist_ind is not None:
        str2 = f"\ncrossover_distribution_index={cross_dist_ind}"

    return str1 + str2


def build_qusbt_config(input_circuit_path,
                       ps_path):
    """
    we assume ./ to be folder tool_model
    this function translates the information from config.json (in the folder tool_model) to a .ini file used by QuSBT
    most of the information in config.json is used to automatically create the .ini
    however, there are some QuSBT settings, specifically the ones regarding the *qusbt_configuration* field, that are not in config.json
    for those settings, the user can modify the file config_qusbt.json (./tools/qusbt)
    """
    #build a folder for quito data made from our resources
    data_folder = Path(QUSBT_PATH,"data")
    qc_name = ps_path.split("/")[-1].replace(".json","")
    ini_file = Path(data_folder, qc_name + ".ini")
    result_folder = Path("./data/results/qusbt")
    if not data_folder.exists():
        data_folder.mkdir()
    if not result_folder.exists():
        result_folder.mkdir()
    

    qc = QuantumCircuit.from_qasm_file(input_circuit_path)
    # print(qc)
    num_qubits = qc.num_qubits
    meas_qubits = []
    for instruction in qc.data:
        if instruction.operation.name == 'measure':
            for q in instruction.qubits:
                meas_qubits.append(qc.find_bit(q).index)
    #program
    p1 = program_part(input_circuit_path, num_qubits, meas_qubits)

    #program_specification
    ps_str = translate_ps(ps_path, num_qubits, meas_qubits)

    #qusbt_configuration
    p3= qusbt_config_part() 

    res = p1+"\n\n"+p3+"\n\n"+ps_str
    #print(res)
    with open(ini_file, "w") as f:
        f.write(res)

    return ini_file


def exec_qusbt(input_circuit_path, ps_path):
    ini_file = build_qusbt_config(input_circuit_path, ps_path)
    qusbt_run(ini_file=ini_file)


