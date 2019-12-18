import collections

from services import aerospike_db
from services.models import Counter


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
			aerospike_db.put((namespace, '/'.join(name_parts), bins['key']), bins)
			aerospike_db.remove(key)

	return wrapper


def add_counter_to_record(counter_id):
	def wrapper(record):
		key, _, _ = record
		aerospike_db.put(key, {str(counter_id): 0})

	return wrapper


def delete_counter(counter_id):
	def wrapper(record):
		key, _, _ = record
		aerospike_db.remove_bin(key, [str(counter_id)])

	return wrapper


def check_counter_overflow(counter_id=None, new_max_value=None):
	overflow = False

	def wrapper(record=None, *, get_overflow=False):
		nonlocal overflow
		if get_overflow:
			return overflow
		key, _, bins = record
		if bins[str(counter_id)] > new_max_value:
			overflow = True

	return wrapper


def convert_results(results):
	for (_, _, bins) in results:
		record = collections.OrderedDict(id=bins['id'])
		for (counter_id, counter_value) in bins.items():
			if counter_id == 'id':
				continue
			counter = Counter.objects.get(id=int(counter_id))
			record[counter.slug] = f"{counter_value}/{counter.max_value}"
		yield record
