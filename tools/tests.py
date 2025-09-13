#%%
import json

string = "{\"type\":\"lunch\"}"

data = json.loads(string)

print(data)
print(type(data))
#%%
