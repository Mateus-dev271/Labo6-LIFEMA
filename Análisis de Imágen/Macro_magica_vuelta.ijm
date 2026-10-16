inputDir  = "D:/AVI_L50/";
outputDir = "D:/RESULTADOS_TIFF/";

x = 245;
y = 380;
w = 1433;
h = 178;

//para la vuelta no los usamos
//primerFrame = 30;
//ultimoFrame = 350;

Threshold_inicial = 106
Threshold_final = 222

File.makeDirectory(outputDir);
list = getFileList(inputDir);
setBatchMode(true);

for (i = 0; i < list.length; i++) {
    archivo = list[i];

    if (endsWith(toLowerCase(archivo), ".avi")) {
        run("AVI...", "select=[" + inputDir + archivo + "] convert");
        tituloOriginal = getTitle();

        // Convierte el video a 8 bits en escala de grises.
        
        makeRectangle(x, y, w, h);

        base = substring(archivo, 0, lengthOf(archivo) - 4);
        nombreCopia = base + "_crop_vuelta";
        carpetaSecuencia = outputDir + nombreCopia + "/";
        File.makeDirectory(carpetaSecuencia);

        // Duplica la selección rectangular y el rango de fotogramas.
        
        	//referencia del largo en frames asi recortamos solo la vuelta
        total = nSlices;
        mitad = (floor(total/2) + 1) - total*0.15;
        run("Duplicate...", "title=[" + nombreCopia + "] duplicate range=" + mitad + "-" + total);

		setThreshold(Threshold_inicial, Threshold_final, "raw");
		setOption("BlackBackground", true);
		run("Convert to Mask", "background=Dark calculate black");
		run("Invert", "stack");
		run("Flip Horizontally");
		
        // Guarda la secuencia TIFF usando la sintaxis registrada por Fiji.
        run("Image Sequence... ", "select=[" + carpetaSecuencia + "] dir=[" + carpetaSecuencia + "] format=TIFF name=" + nombreCopia);

        close();
        selectWindow(tituloOriginal);
        close();
    }
}

setBatchMode(false);
print("Proceso terminado.");