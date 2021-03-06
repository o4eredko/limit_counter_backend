import aerospike
from aerospike import exception

config = {
	'hosts': [("aerospike", 3000)],
	'policies': {'key': aerospike.POLICY_KEY_SEND},
}

try:
	aerospike_db = aerospike.client(config).connect()
except (exception.TimeoutError, exception.ClientError):
	import sys

	print("failed to connect to the cluster with", config['hosts'])
	sys.exit(1)
