def calculate_series(n):
    total = 0.0
    for i in range(n):
        term = (-1) ** i / (2 * i + 1)
        total += term
    return total * 4

# Calculate the first 10,000 terms
result = calculate_series(10000)
print(result)