# Multiple parameters

This is the function to be tested, it receive x bits and convert it to an integer.

```py
def bytes_to_integer(*bit: int):
    how_many = len(bit)
    result = 0

    for i in range(how_many):
        offset = 2**(how_many - 1 - i)
        result += bit[i] * offset

    return result
```

This have 16 possible values, we can build all cases providing the bit 3 and 4 as 00, 01, 10, 11 in row, and in each iteration set the bit 1 and 2
starting from 00 until 11, like it where in the following table.

| Decimal | 4-bit Binary |
| ------- | ------------ |
| 0       | 0000         |
| 1       | 0001         |
| 2       | 0010         |
| 3       | 0011         |
| 4       | 0100         |
| 5       | 0101         |
| 6       | 0110         |
| 7       | 0111         |
| 8       | 1000         |
| 9       | 1001         |
| 10      | 1010         |
| 11      | 1011         |
| 12      | 1100         |
| 13      | 1101         |
| 14      | 1110         |
| 15      | 1111         |

So, the bit 1 have a value of 8, the bit 2 is 4, the bit 3 is 2, and the bit 1 is 1 or 0, it can sum each component and check if the result is ok.

```py
@pytest.mark.parametrize('bit1,bit2,res1', [(0, 0, 0), (0, 1, 4), (1, 0, 8), (1, 1, 12)])
@pytest.mark.parametrize('bit3,bit4,res2', [(0, 0, 0), (0, 1, 1), (1, 0, 2), (1, 1, 3)])
def test_bytes_to_integer(bit1, bit2, bit3, bit4, res1, res2):
    number = bytes_to_integer(bit1, bit2, bit3, bit4)
    assert number == res1 + res2
```

This test will be executed 16 times with each row in the table, this avoid to write the test 16 times or use random values that should generate a random behavior, this case pass each one of the case have a significant overhead when the tests are running, it's recommended when the functionality is core or important in the api.
