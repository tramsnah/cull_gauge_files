'''
Test code for 'cull_gauge_file'
'''
import cull_gauge_file as cgf

#filename=r"test_data\tiny_test_2.cli"
#cull_gauge_file(filename, ncull=3, do_export=True)

filename=r"test_data\tiny_test.cli"
cgf.cull_gauge_file(filename, ncull=3, do_export=True)

filename=r"test_data\tiny_41235.asc"
cgf.cull_gauge_file(filename, ncull=5, do_export=True)

filename=r"test_data\tiny_44147.ASC"
cgf.cull_gauge_file(filename, ncull=10, do_export=True)

filename=r"test_data\tiny_44147_B.ASC"
df = cgf.cull_gauge_file(filename, ncull=10, do_export=True)

filename=r"test_data\tiny_44147.tsv"
cgf.cull_gauge_file(filename, ncull=10, do_export=True)

filename=r"test_data\tiny_44147.csv"
cgf.cull_gauge_file(filename, ncull=10, do_export=True)

filename=r"test_data\44147.ASC"
cgf.cull_gauge_file(filename, do_export=True)

filename=r"test_data\60759.tpr"
cgf.cull_gauge_file(filename, ncull=100, do_export=True)

