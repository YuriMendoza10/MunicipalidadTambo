import mysql.connector

db = mysql.connector.connect(
	host="localhost",
	user = "root",
	password= "root",
	database = 	"bd_municipalidad",
	port=3306
)
print(db)