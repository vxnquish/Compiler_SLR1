import sys
from parser import parser  # type: ignore # import your implementation

def read_tokens(path: str) -> list:
    with open(path) as f:
        return f.read().split()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main.py <input_file>")
        sys.exit(1)

    tokens = read_tokens(sys.argv[1])
    ok, result = parser(tokens)
    if ok:
        print("Accepted")
        print(result)
    else:
        print(f"Error at token {result.position}: {result.message}")