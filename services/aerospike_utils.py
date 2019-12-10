from services import aerospike


def update_set_name(old_name_part, new_name_part):
	def wrapper(record):
		key, _, bins = record
		namespace, set_name, *_ = key
		name_parts = set_name.split('/')
		try:
			index = name_parts.index(old_name_part)
		except ValueError:
			return
		else:
			name_parts[index] = new_name_part
			aerospike.put((namespace, '/'.join(name_parts), bins['key']), bins)
			aerospike.remove(key)

	return wrapper


def delete_set(*, platform=None, element=None):
	def wrapper(record):
		key, _, bins = record
		_, set_name, *_ = key
		name_parts = set_name.split('/')
		if platform is not None and platform in name_parts:
			aerospike.remove(key)
		elif element is not None and element == name_parts[1]:
			aerospike.remove(key)

	return wrapper


def add_counter_to_record(counter_id):
	def wrapper(record):
		key, _, _ = record
		aerospike.put(key, {counter_id: 0})

	return wrapper


def delete_counter(counter_id):
	def wrapper(record):
		key, _, _ = record
		aerospike.remove_bin(key, [counter_id])

	return wrapper

#
# def delete_record(record):
# 	key, _, _ = record
# 	aerospike.remove(key)
