# -*- coding: utf-8 -*-
"""
 * @Date: 2021-06-15 09:49:37
 * @LastEditors: Hwrn
 * @LastEditTime: 2021-06-19 11:43:41
 * @FilePath: /Work/home/hwrn/Data/Database2/KEGG/Scripts/modules.py
 * @Description:
"""

import os
import re
from typing import Dict, List, Tuple
from io import FileIO

from PyLib.biotool.kegg import query
from PyLib.biotool.kegg.kegg import KModule


KEGG_DIR = '/home/hwrn/Data/Database2/KEGG/module'


METHODS = ['']


def TPM_FORMAT(method):
    return f'03_annot/tpm/{method}.tpm'


def KO_FORMAT(method):
    return f'03_annot/funct/{method}/{method}-KO.tsv'


def KEGG_MAP_FORMAT(method):
    return f'Analyze/pathway/{method}-KEGG.txt'


def load_module_levels(brite: Dict):
    module_levels = []
    modules: List[Tuple[str, KModule]] = []
    for modules1_name, modules1 in brite.items():
        for metabolism_name, metabolism in modules1.items():
            for metabolism_name2, metabolism2 in metabolism.items():
                for entry, name in metabolism2.items():
                    module_levels.append((modules1_name, metabolism_name,
                                          metabolism_name2, entry, name))
                    raw_module = query.load_KEGG_module_raw(entry, KEGG_DIR)
                    module = KModule(''.join(raw_module['DEFINITION']),
                                     additional_info=''.join(raw_module['NAME']))
                    modules.append((entry, module))
    return module_levels, modules


def KO_abd_sample(method: str):
    # first load KO and genes
    gene_KO: Dict[str, str] = {}
    with open(KO_FORMAT(method)) as tab_in:
        for line in tab_in:
            gene, KO = line.split()
            gene_KO[gene] = KO
    KO_abundance: Dict[str, float] = {}
    with open(TPM_FORMAT(method)) as tab_in:
        for line in tab_in:
            gene, abundance = line.split()
            KO = gene_KO.get(gene, '')
            if KO:
                KO_abundance[KO] = KO_abundance.get(KO, 0) + float(abundance)
    return {KO: abundance for KO, abundance in KO_abundance.items()}


def list_module_from_kegg(file: FileIO):
    MODULE_PATTERN = re.compile(r'^M\d{5}\s+')
    for group in (re.match(MODULE_PATTERN, line) for line in file):
        if group:
            yield group.group().strip()


def compare_local_online(method,
                         modules: List[Tuple[str, KModule]],
                         KO_abundance: Dict[str, float]):
    with open(KEGG_MAP_FORMAT(method)) as file_in:
        modules1 = set(list_module_from_kegg(file_in))
    modules2 = {entry for (entry, module) in modules
                if int(module.completeness(KO_abundance))}
    print(method, modules1 - modules2, modules2 - modules1)


def main():
    module_name = f'Analyze/pathway/module_name.tsv'
    existance = f'Analyze/pathway/exist.tsv'
    abundance = f'Analyze/pathway/abundance.tsv'

    # first load KEGG modules
    ko00002 = query.load_brite('br:ko00002',
                               os.path.join(KEGG_DIR, '../brite', 'ko00002.json'))[1]
    module_levels, modules = load_module_levels(ko00002)
    with open(module_name, 'w') as file_out:
        print('A\tB\tC\tentry\tname',
              *('\t'.join(module_level) for module_level in module_levels),
              sep='\n', file=file_out)
    with open(abundance, 'w') as abd_out, \
            open(existance, 'w') as exi_out:
        print('# sample',
              *(entry for entry, _ in modules),
              sep='\t', file=abd_out)
        print('# sample',
              *(entry for entry, _ in modules),
              sep='\t', file=exi_out)
        for method in METHODS:
            KO_abundance = KO_abd_sample(method)
            compare_local_online(method, modules, KO_abundance)
            print(method,
                  *(int(module.completeness(KO_abundance))
                    for entry, module in modules),
                  sep='\t', file=exi_out)
            print(method,
                  *(module.abundance(KO_abundance)
                    for entry, module in modules),
                  sep='\t', file=abd_out)


if __name__ == '__main__':
    main()
