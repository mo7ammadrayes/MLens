
import os
import csv
import pandas
x=12
if(x<4):
    print("siu",x)

while (x<=10):
    print(x)
    x*=2

print("hello wrolD ".capitalize()
      )

print("sii"*3)

#using lists sett list x =y this makes coppy if i do x=y[:] this makes new one 

for i in range(-10,-1,-1):
     print()
    # 



xx=[22,1,3,4,2,4,321]

# for i,element in enumerate(xx):
#     print(element,type(element))

print(xx[:4])

print(xx[::-1])
print(xx[5:1:-1])

setx ={2,3,45}
print(6 in setx)


dictx={"key": "value"}
dictx[9]=4 # type: ignore

print(dictx)
print(dictx[9])
print(dictx.values())
del dictx[9]
print(dictx)

mapx =[3,2,3,4,432,2,25]
mp =map(lambda i:i+3,mapx)
print(list(mp))

filterx =[3,2,3,4,432,2,25]
fil = filter(lambda i:(i+2)%2==0,filterx)
print(list(fil))


x= open('data/S.csv', 'r') 
# print(x.read(3))
# print(x.readline())
# print(x.readline())

for line in x:
    print(line)

x.close()

if not os.path.exists("data/test.txt"):
    f=open("test.txt","x")
    f.write("testing ")
    f.close()

if os.path.exists("data/Q.csv"):
    os.remove("data/Q.csv")
else:
    print("file not here ")

with open("data/G.csv","a")as f:
    f.write("siuu\n")

with open("data/G.csv","r")as ff:
    print(ff.read())



#r = read
#x=create
# w=write (overwirte)
# a= append 


# with open("data/setF.csv","r") as file:
#     # reader =csv.reader(file)
#     reader =csv.DictReader(file)

#     # next(reader)
#     conut=0
#     for row in reader:
#         conut+=1
#         print(row["IsControl"])
#         # print(row[1])

#     print(conut)

data_col= pandas.read_csv("data/setF.csv")
print(data_col)
countx=0
for col in data_col:
    print(col)
    countx+=1
print(countx)
