import csv

def lines_to_csv(input_file, output_file, lines_per_row=6):
    """
    Read a text file and write a CSV where every N lines become columns in a row.
    
    Args:
        input_file: Path to input text file
        output_file: Path to output CSV file
        lines_per_row: Number of lines to group as columns (default: 6)
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f]
    
    # Group lines into chunks of specified size
    rows = []
    for i in range(0, len(lines), lines_per_row):
        chunk = lines[i:i + lines_per_row]
        # Pad with empty strings if last chunk is incomplete
        while len(chunk) < lines_per_row:
            chunk.append('')
        rows.append(chunk)
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    print(f"Successfully wrote {len(rows)} rows to {output_file}")

# Usage
if __name__ == "__main__":
    input_file = "data.txt"
    output_file = "output.csv"
    
    lines_to_csv(input_file, output_file, lines_per_row=6)

