import os

path = os.path.join('data', 'test_large.csv')
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w', encoding='utf-8') as f:
    f.write('col1,col2,col3\n')
    row = ','.join(['a'*1000, 'b'*1000, 'c'*1000]) + '\n'
    while os.path.getsize(path) < 11 * 1024 * 1024:
        f.write(row)
print('Created', path, 'size', os.path.getsize(path))
