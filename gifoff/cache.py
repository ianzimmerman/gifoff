from flask_caching import Cache, make_template_fragment_key

cache = Cache(config={'CACHE_TYPE': 'simple'})

def clear_keys(cache, keys):
	for key in keys:
		cache.delete(make_template_fragment_key(key))