f=open('nodes1.csv')
lines1 = f.readlines()
for i in range(len(lines1)):
    lines1[i] = lines1[i].split(';')[0]
print(len(lines1))

f=open('nodes2.csv')
lines2 = f.readlines()
for i in range(len(lines2)):
    lines2[i] = lines2[i].split(';')[0]
print(len(lines2))
c=0
for i in range(len(lines1)):
    if lines1[i] not in lines2:
        print(lines1[i])
        c+=1
print(c)


