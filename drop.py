"""
Computes the grams in 1 drop of water.
"""
#%%

nom_flow_rate_ul_min = 30.9 
num_flow_rate_ul_s = nom_flow_rate_ul_min / 60.0  
print(f"Flow rate: {num_flow_rate_ul_s:.4f} uL/s")

seconds_per_drop = 12
grams_per_drop = num_flow_rate_ul_s * seconds_per_drop / 1000.0
print(f"Milliliters per drop: {grams_per_drop:.4f} mL")
print(f"Grams per drop: {grams_per_drop:.4f} g")