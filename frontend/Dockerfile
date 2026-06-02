# Usamos el servidor web ligero
FROM nginx:alpine

# Copiamos TU archivo index.html y lo metemos dentro de las tripas de Nginx
COPY index.html /usr/share/nginx/html/index.html

# Le decimos al sistema que este contenedor se comunica por el puerto 80
EXPOSE 80
