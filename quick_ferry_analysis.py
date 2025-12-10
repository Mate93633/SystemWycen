#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

# Prostsza analiza bez pandas
ferry_costs = {}

with open(r'c:\Users\Mateusz Bartosik\Downloads\promy.csv', 'r', encoding='utf-8') as f:
    lines = f.readlines()[1:]  # Skip header
    
    for line in lines:
        parts = line.strip().split(';')
        if len(parts) >= 2:
            ferry = parts[0].strip().upper()
            try:
                cost = float(parts[1].replace(',', '.'))
                if cost > 0 and cost < 5000:  # Filter outliers
                    if ferry not in ferry_costs:
                        ferry_costs[ferry] = []
                    ferry_costs[ferry].append(cost)
            except:
                pass

# Calculate averages
results = []
for ferry, costs in ferry_costs.items():
    if len(costs) >= 5:  # Minimum 5 trips
        avg = sum(costs) / len(costs)
        results.append((ferry, len(costs), avg, min(costs), max(costs)))

# Sort by count
results.sort(key=lambda x: x[1], reverse=True)

# Write to file
with open(r'c:\Users\Mateusz Bartosik\Projekty python\SystemWycen\ferry_results.txt', 'w', encoding='utf-8') as f:
    f.write("ANALIZA KOSZTÓW PROMÓW\n")
    f.write("="*80 + "\n\n")
    
    for ferry, count, avg, min_c, max_c in results[:50]:  # Top 50
        f.write(f"{ferry}\n")
        f.write(f"  Przejazdy: {count}\n")
        f.write(f"  Średni koszt: {avg:.2f} EUR\n")
        f.write(f"  Min: {min_c:.2f} EUR\n")
        f.write(f"  Max: {max_c:.2f} EUR\n")
        f.write("-"*80 + "\n")

print("Done! Results saved to ferry_results.txt")
