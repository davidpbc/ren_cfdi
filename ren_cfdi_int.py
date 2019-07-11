# -*- coding: utf-8 -*-
'''
Título              : ren_cfdi_int.py
Descripción         : Interfaz para Procesador de archivos XML de CFDi
                      Ayuda en el procesamiento masivo de CFDis
Autor               : David Padilla (mods Aztecos)
Fecha (creación)    : 11/09/2018
Fecha (modificación): 29/09/2018
Fecha (modificación): 09/10/2018 Aztecos
Versión             : 1.5
Uso                 : Interfaz que utiliza el módulo ren_cfdi.py
                      - Ejecutar:
                      python ren_cfdi_int.py
                      - (Opcional) Insertar un folio para el lote de archivos.
                      - Seleccionar carpeta donde se ubican los archivos XML.
                      - Seleccionar la opción 'CSV' si se requiere un reporte
                      - Hacer click sobre el botón 'Procesar'
                      - Hacer click sobre el botón 'Salir' al finalizar.
'''
from tkFileDialog import askdirectory
from Tkinter import *
import sys
import os
from ren_cfdi import CFDi

class mainWindow(object):
    """
    Interfaz básica con Tkinter para la ejecución del script
    """
    def __init__(self, master):
        self.master = master
        self.fileCsvName = False

        # Entrada de Texto 'Folio' {CP.ACS: }
        Label(master, text="Folio").grid(row=0)
        self.e1 = Entry(master)
        self.e1.grid(row=0, column=1)
        self.e1.focus()

        # Botón de selección de 'Directorio'
        Label(master, text="Directorio de Archivos").grid(row=1)
        self.e2 = False
        Button(master, text="Buscar", command=self.browse_directory).grid(row=1, column=1)

        # Check para generar 'CSV'
        self.e3 = IntVar()
        Checkbutton(master, text="CSV", variable=self.e3).grid(row=2, sticky=W)
        self.e3.set(1)

        # C.P. ACS Check para generar 'sóloReporte'
        self.e4 = IntVar()
        Checkbutton(master, text="sinRenombrar", variable=self.e4).grid(row=3, sticky=W)

        # C.P. ACS Check para usar criterio 'Ventas'
        self.e5 = IntVar()
        #Checkbutton(master, text="Ventas", variable=self.e5).grid(column=2, row=3, sticky=W)

        # Botones de Acción
        Button(master, text='Salir', command=master.quit).grid(row=5, column=0, sticky=W, pady=4)
        Button(master, text='Procesar', command=self.process_files).grid(row=5, column=1, sticky=W, pady=4)

    def browse_directory(self):
        """
        Asigna el Directorio de archivos seleccionado a la variable 'e2'.
        """
        folderName = askdirectory()
        sys.stdout.write("{}.\n".format(folderName))
        self.e2 = folderName

    def process_files(self):
        """
        Procesa todos los archivos contenidos por el Directorio almacenado
        en la variable 'e2', si son XML los procesa utilizando la clase CFDi.
        """
        if not self.e2:
            sys.stdout.write("No proporcionó un directorio.\n")
            self.master.quit()
        sys.stdout.write("Folio: %s\nFolder: %s\nCSV: %s\n" \
            % (self.e1.get(), self.e2, self.e3.get()))
        if self.e3.get:
            self.generate_csv()
        for root, dirs, files in os.walk(self.e2):
            for name in files:
                if name.split(".")[-1].upper() in ("XML"):
                    filename = "{}{}{}".format(self.e2, os.sep, name)
                    sys.stdout.write("{}\n".format(filename))
                    fileCfdi = CFDi(filename, self.e1.get().upper())
                    sys.stdout.write("Valores: {}\n\n".format(str(fileCfdi.values)))
                    if not self.e4.get():
                        sys.stdout.write("==========Cambiando nombre de Archivo: =========\n{}\n".format(fileCfdi.fileName))
                        fileCfdi.rename_file()
                    if self.e3.get():
                        fileCfdi.generate_csv_line(self.fileCsvName)

    def generate_csv(self):
        """
        Genera un archivo CSV con una fila que contiene los encabezados.
        """
        fileCsvName = "{}{}reportecfdi.csv".format(self.e2, os.sep)
        if os.path.isfile(fileCsvName):
            os.remove(fileCsvName)
        header = self.get_csv_header()
        f = open(fileCsvName, 'a')
        f.write("{}\n".format(header))
        f.close()
        self.fileCsvName = fileCsvName

    def get_csv_header(self):
        """
        Genera la primera fila del CSV con el encabezado de las columnas.
        """
        vals = []
        vals.append('Archivo')
        vals.append('RFC Emisor')
        vals.append('RFC Receptor')
        vals.append('UUID')
        vals.append('Folio')
        vals.append('NumEmpleado')#  mod C.P. ACS
        vals.append('Sub Total')
        vals.append('Descuento')
        vals.append('Total')
        vals.append('Traslados')
        vals.append('ISR')
        vals.append('IVA')
        vals.append('IEPS')
        vals.append('Retenciones')
        vals.append('ISR')
        vals.append('IVA')
        vals.append('Percepciones')
        vals.append('Otros Pagos')
        vals.append('Deducciones')
        vals.append('Dedducción ISR')
        vals.append('Neto')
        vals.append('M.P.')
        vals.append('Tipo')
        vals.append('Versión')
        vals.append('ImpPagado')
        vals.append('=SUMA(Y2:Y9999)')
        return ",".join(vals)


if __name__ == "__main__":
    root = Tk()
    m = mainWindow(root)
    root.mainloop()
