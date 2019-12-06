import aerospike
from aerospike import exception

config = {
	'hosts': [('172.28.128.4', 3000)],
	'policies': {'timeout': 1200},
}

try:
	client = aerospike.client(config).connect()
except exception.TimeoutError:
	import sys

	print("failed to connect to the cluster with", config['hosts'])
	sys.exit(1)
