# Permite usar PyMySQL (100% Python, fácil de instalar en Windows y EC2)
# como driver de MySQL en lugar de mysqlclient.
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
