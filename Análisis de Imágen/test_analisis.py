import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import tifffile
import imageio.v2 as imageio
from skimage.morphology import skeletonize
from skimage.morphology import medial_axis
from skimage.morphology import thin
from scipy import ndimage as ndi
from skimage.graph import route_through_array

#%%  #carga de imagens (tiff binarizadas) para analizar

# Carpeta donde están las imágenes
carpeta = r"C:\Users\mainumbi\Documents\Labo 6-7\juan-mateo\datos\26-09-10\videos\TIFF_binarizado\v_50_45px"

# Buscar todos los .tif
archivos = glob.glob(os.path.join(carpeta, "*.tif"))

# Ordenar las imágenes
archivos.sort()

# Cargar todas las imágenes
imagenes = [tifffile.imread(f) for f in archivos]

# Crear el stack
stack = np.stack(imagenes)

print("Dimensiones del stack (nro imag, Xpx, Ypx):", stack.shape)
print("Tipo de datos:", stack.dtype)

#plot de una imagen, puro sanity check
plt.imshow(stack[5], cmap="gray")
plt.show()

#%%  #construccion de imagen representativa

#parametros para modificar

margen = 30 #pixeles que dejamos de margen a izq y der al recortar las imagenes
frame_inicial = 150
ventana_temporal = 50 #frames que usamos para costruir la imagen representativa 
umbral = 250 # threshold usado luego de calular mean y median

#%%%

#elijo la imagen central para definir la region de interes
centro = int(len(stack)*0.75)
plantilla = stack[centro]


#calculo limite derecho
lim_der = np.where(plantilla[0] == 255)[0][-1]

#calculo limite izquierdo
for j in range(len(plantilla)):

    lim_izq = np.where(plantilla[-j-1] == 255)[0]
    
    if len(lim_izq) != 0:
        break

lim_izq = lim_izq[0]

#prints
roi =  lim_der - lim_izq

print("lim_izq =",lim_izq)
print("lim_der =",lim_der)
print("roi =",roi)
print("margen =",margen)

#itero para todas las imagenes
stack_recortado = []

for i in range(len(stack) - frame_inicial):

    #defino la imagen a recortar
    imagen = stack[i + frame_inicial]
    
    #eligo el limite derecho de la imagen
    limite = np.where(imagen[0] == 255)[0][-1]

    #recorto la imagen
    imagen_recortada = imagen[: , limite - roi - margen : limite + margen]
    
    #guardo el recorte
    stack_recortado.append(imagen_recortada)

#tomo los frames que quiero usar
stack_recortado = np.array(stack_recortado[ventana_temporal:-ventana_temporal])

#imagen promediando 
mean_image = np.mean(stack_recortado, axis=0)
representative_mean = (mean_image >= umbral).astype(np.uint8)

#imagen con la mediana
median_image = np.median(stack_recortado, axis=0)
representative_median = (median_image >= umbral).astype(np.uint8)

#graficos
fig, axes = plt.subplots(1, 2, figsize=(8, 5), dpi = 150)

axes[0].imshow(representative_mean, cmap='gray', vmin=0, vmax=1)
axes[0].set_title('Mean')
axes[0].axis('off')

axes[1].imshow(representative_median, cmap='gray', vmin=0, vmax=1)
axes[1].set_title('Median')
axes[1].axis('off')

plt.tight_layout()
plt.show()



#%%  #gifs y videos

#creo un gif
imageio.mimsave("resultado_stack.gif", stack_recortado, fps=10, loop=0)

print("¡GIF guardado con éxito como 'resultado_stack.gif'!")

# Nombre del archivo de salida
nombre_video = "video_salida.mp4"

# fps: cuadros por segundo (ajusta la velocidad del video)
fps = 10 

# Guardar el video
with imageio.get_writer(nombre_video, fps=fps, codec='libx264') as writer:
    for img in stack_recortado:
        writer.append_data(img)

print(f"¡Video guardado con éxito como '{nombre_video}'!")

#%%  #skelenotizacion

# Si tu imagen_recortada es uint8 con 0 y 255, conviértela.
binarized_image = representative_mean > 0 # Esto convertirá 255 a True y 0 a False

# Aplicar la esqueletización
skeleton = skeletonize(binarized_image)
esqueleto = medial_axis(binarized_image)
skeleton_lee = skeletonize(binarized_image, method='lee')
skeleton_thin = thin(binarized_image)

#hago todas las sumas con el medial axis xq es el unico que detecta bien la parte de arriba de la imagen
suma_skeletonize = skeleton + esqueleto
suma_lee = skeleton_lee + esqueleto
suma_thin = skeleton_thin + esqueleto

#todas las sumas skeletonizadas zhang
suma_skeletonized_skl =skeletonize(suma_skeletonize)
suma_lee_skl = skeletonize(suma_lee)
suma_thin_skl = skeletonize(suma_thin)

#todas las sumas thin
suma_skeletonized_thin =thin(suma_skeletonize)
suma_lee_thin = thin(suma_lee)
suma_thin_thin = thin(suma_thin)

#todas las sumas lee
suma_skeletonized_lee =skeletonize(suma_skeletonize, method='lee')
suma_lee_lee = skeletonize(suma_lee, method='lee')
suma_thin_lee = skeletonize(suma_thin, method='lee')

print("\n--- Propiedades del Esqueleto ---")
print("Forma del esqueleto:", skeleton.shape)
print("Tipo de datos (dtype) del esqueleto:", skeleton.dtype)

#%%  #graficos de skeletonizacion

#zoom arriba
zoom_x_inicial = 600
zoom_x_final = 750
zoom_y_inicial = 100
zoom_y_final = 0

#zoom abajo
#zoom_x_inicial = 0
#zoom_x_final = 90
#zoom_y_inicial = 250
#zoom_y_final = 150

#sin zoom
#zoom_x_inicial = 0
#zoom_x_final = len(representative_median[0])
#zoom_y_inicial = len(representative_median)
#zoom_y_final = 0


# Visualizar la imagen original recortada y su esqueleto
fig, axes = plt.subplots(1, 4, figsize=(12, 6), dpi = 150)
fig.suptitle('métodos de skeletonización', )

#axes[0].imshow(imagen_recortada, cmap='gray')
#axes[0].set_title('Imagen Binarizada Recortada')

for ax in axes:

    ax.set_xlim(zoom_x_inicial, zoom_x_final)        
    ax.set_ylim(zoom_y_inicial, zoom_y_final)
    ax.grid()


axes[0].imshow(skeleton, cmap='gray')
axes[0].set_title('skeletonize zhang')
axes[0].imshow(representative_median, cmap='gray',alpha=0.5)

axes[1].imshow(skeleton_lee, cmap='gray')
axes[1].set_title('skeletonize lee')
axes[1].imshow(representative_median, cmap='gray',alpha=0.5)

axes[2].imshow(skeleton_thin, cmap='gray')
axes[2].set_title('thin')
axes[2].imshow(representative_median, cmap='gray',alpha=0.5)

axes[3].imshow(esqueleto, cmap='gray')
axes[3].set_title('medial axis')
axes[3].imshow(representative_median, cmap='gray',alpha=0.5)

plt.show()

#visualizar suma de métodos (todos más medial axis)
fig, axes = plt.subplots(1, 3, figsize=(12, 6), dpi = 150)
fig.suptitle('suma', fontsize=16)
for ax in axes:
    ax.set_xlim(zoom_x_inicial, zoom_x_final)        
    ax.set_ylim(zoom_y_inicial, zoom_y_final)
    ax.grid()

axes[0].imshow(suma_skeletonize, cmap='gray')
axes[0].set_title('zhang + medial axis')
axes[0].imshow(representative_median, cmap='gray',alpha=0.5)

axes[1].imshow(suma_thin, cmap='gray')
axes[1].set_title('thin + medial axis')
axes[1].imshow(representative_median, cmap='gray',alpha=0.5)

axes[2].imshow(suma_lee, cmap='gray')
axes[2].set_title('lee + medial axis')
axes[2].imshow(representative_median, cmap='gray',alpha=0.5)

plt.show()

#visualizar zhang de cada suma
fig, axes = plt.subplots(1, 3, figsize=(12, 6), dpi = 150)
fig.suptitle('skeletonizacion zhang de la suma', fontsize=16)
for ax in axes:
    ax.set_xlim(zoom_x_inicial, zoom_x_final)        
    ax.set_ylim(zoom_y_inicial, zoom_y_final)
    ax.grid()

axes[0].imshow(suma_skeletonized_skl, cmap='gray')
axes[0].set_title('zhang + medial axis')
axes[0].imshow(representative_median, cmap='gray',alpha=0.5)

axes[1].imshow(suma_thin_skl, cmap='gray')
axes[1].set_title('thin + medial axis')
axes[1].imshow(representative_median, cmap='gray',alpha=0.5)

axes[2].imshow(suma_lee_skl, cmap='gray')
axes[2].set_title('lee + medial axis')
axes[2].imshow(representative_median, cmap='gray',alpha=0.5)

plt.show()

#visualizar Lee de cada suma
fig, axes = plt.subplots(1, 3, figsize=(12, 6), dpi = 150)
fig.suptitle('skeletonizacion Lee de la suma', fontsize=16)
for ax in axes:
    ax.set_xlim(zoom_x_inicial, zoom_x_final)        
    ax.set_ylim(zoom_y_inicial, zoom_y_final)
    ax.grid()

axes[0].imshow(suma_skeletonized_lee, cmap='gray')
axes[0].set_title('zhang + medial axis')
axes[0].imshow(representative_median, cmap='gray',alpha=0.5)

axes[1].imshow(suma_thin_lee, cmap='gray')
axes[1].set_title('thin + medial axis')
axes[1].imshow(representative_median, cmap='gray',alpha=0.5)

axes[2].imshow(suma_lee_lee, cmap='gray')
axes[2].set_title('lee + medial axis')
axes[2].imshow(representative_median, cmap='gray',alpha=0.5)

plt.show()

#visualizar thin de cada suma
fig, axes = plt.subplots(1, 3, figsize=(12, 6), dpi = 150)
fig.suptitle('thin de la suma', fontsize=16)
for ax in axes:
    ax.set_xlim(zoom_x_inicial, zoom_x_final)        
    ax.set_ylim(zoom_y_inicial, zoom_y_final)
    ax.grid()

axes[0].imshow(suma_skeletonized_thin, cmap='gray')
axes[0].set_title('zhang + medial axis')
axes[0].imshow(representative_median, cmap='gray',alpha=0.5)

axes[1].imshow(suma_thin_thin, cmap='gray')
axes[1].set_title('thin + medial axis')
axes[1].imshow(representative_median, cmap='gray',alpha=0.5)

axes[2].imshow(suma_lee_thin, cmap='gray')
axes[2].set_title('lee + medial axis')
axes[2].imshow(representative_median, cmap='gray',alpha=0.5)

plt.show()

#%%  #diferencia de velocidades 

X_punta = []
Y_punta = []

stack_long_t = stack_recortado[15:] #stack conrecorte espacial y aca elijo el recorte temporal

for m in range(len(stack_long_t)):
    
    frame = stack_long_t[m]

    for j in range(len(frame)):

        x_punta = np.where(frame[-j-1] == 255)[0]
    
        if len(x_punta) != 0:
            break

    x_punta = x_punta[0]
    y_punta = len(frame)-j-1
    
    X_punta.append(x_punta)
    Y_punta.append(y_punta)

tiempo_plot = np.linspace(0,len(stack_long_t),len(stack_long_t))

fig, ax = plt.subplots(2, 2, figsize=(12, 6), dpi = 150)

ax[0][0].plot(tiempo_plot, X_punta,"-*")
ax[0][0].set_title('X')
ax[0][0].grid()

ax[0][1].plot(tiempo_plot, Y_punta,"-*")
ax[0][1].set_title('Y')
ax[0][1].grid()

ax[1][0].plot(tiempo_plot[:-1], np.diff(X_punta),"-*")
ax[1][0].set_title('V_X')
ax[1][0].grid()

ax[1][1].plot(tiempo_plot[:-1], np.diff(Y_punta),"-*")
ax[1][1].set_title('V_Y')
ax[1][1].grid()

plt.show()

#%%  #skeletonizacion via la geodesica

#calculo el punto inicla

left  = np.where(representative_median[0] == 1)[0][0]
right = np.where(representative_median[0] == 1)[0][-1]

x_inicial = int((left + right)*0.5)
y_inicial = 0


#abajo
for j in range(len(representative_median)):

    x1 = np.where(representative_median[-j-1] == 1)[0]
    
    if len(x1) != 0:
        break

x1 = x1[0]
y1 = len(representative_median)-j-1

#arriba
busqueda=[]

for k in range(45):
    
    busqueda.append(np.where(representative_median[y1-k] == 1)[0][0])

x2 = np.min(busqueda)
y2 = y1 - np.argwhere(busqueda==np.min(busqueda))[-1]

#final

x_final = int((x1 + x2)*0.5)
y_final = int((y1 + y2)*0.5)

#grafico de los puntos inicial y final 
plt.imshow(representative_median, cmap='gray', vmin=0, vmax=1)
plt.scatter(x_inicial, y_inicial)
plt.scatter(x_final, y_final)
plt.xlim(10,60)
plt.ylim(220,180)
plt.grid()
plt.title('Median')


#%%

#calcula distancia al borde
distancias = ndi.distance_transform_edt(representative_median)

#invierte para abaratar el costo del centro
cost_map = distancias.max() - distancias + 0.5

#encarece la parte exterior al filamento
#cost_map[~representative_median] = 999999

#incerto extremos y calculo geodesica
start = (y_inicial, x_inicial)
end = (y_final, x_final)

path, cost = route_through_array(cost_map, start, end, fully_connected=True, geometric=True)

# Convertir el camino a un array para graficarlo
path = np.array(path)

# Mostrar el resultado
plt.imshow(representative_median, cmap='gray')
plt.scatter(x_inicial, y_inicial)
plt.scatter(x_final, y_final)
plt.plot(path[:, 1], path[:, 0], color='red', linewidth=2, label='Eje Central')
plt.xlim(700,750)
plt.ylim(20,0)
plt.legend()
plt.show()







