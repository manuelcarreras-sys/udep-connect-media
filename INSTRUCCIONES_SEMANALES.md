# Instrucciones para producir la semana (UDEP Connect)

1. Leer README.md (reglas obligatorias) y REGISTRO.md (lo publicado y conteo del mes; máximo 20 por mes).
2. Planear ~5 publicaciones para los próximos 7 días sin repetir ganchos: rotar bachillerato, licenciaturas (cada carrera), maestrías y temas generales (RVOE, plataforma, preguntas frecuentes).
3. Escribir un JSON por publicación en contenido/ (ver ejemplos), con "fecha" y "texto". 19:00 entre semana, 18:00 fin de semana (CDMX).
4. Generar con `python3 tools/gen.py <json> [--preview]` y revisar cada imagen/fotograma antes de publicar.
5. Commit + push; verificar 200 en raw.githubusercontent.com.
6. Programar en Metricool (blogId 7886621, instagram + facebook, Reels como REEL, carruseles como POST).
7. Anotar en REGISTRO.md con el ID de Metricool y actualizar el conteo.
8. VERIFICAR: después de programar, consultar getScheduledPosts (blogId 7886621, timezone America/Mexico_City) y confirmar que cada publicación tiene la fecha y hora correctas. Revisar también que las de la semana anterior hayan quedado con status PUBLISHED. Si alguna hora aparece movida (por ejemplo 02:00 en vez de 19:00), corregirla con updateScheduledPost y avisar a Juan.
