La "macro mágica" es la que se encarga de hacer el análisis en fiji de forma automática. Hay una version para la ida y una para la vuelta porque la forma de recortar los frames es distinta, y tambien se agrega la funcion de "flip horizontally" para la vuelta, lo cual hace que el código de python sea el mismo.

Los códigos llamados "test_análisis" contieen versiones de prueba de las funciones que fuimos implementando en el código 
final llamado "analisis_imagen". 
"transitorio" contiene lo que utilizamos para estudiar los frames en donde el filamento continúa deformandose. Al final
terminamos implementando parte de ese análisis en "analisis_imagen".

luego de pasar un video por "analisis_imagen" lo que extraemos es la velocidad del motor (pasado por la calibracion del motor)
ademas de la amplitud maxima en X e Y de la curvatura y el tiempo que tarda en llegar al estacionario.

