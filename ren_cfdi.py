# -*- coding: utf-8 -*-
'''
Título              : ren_cfdi.py
Descripción         : Procesador de archivos XML de CFDi
Autor               : David Padilla
Fecha (creación)    : 11/09/2018
Fecha (modificación): 29/09/2018
Versión             : 1.2
Uso                 : Módulo que requiere de una función pricipal
                      - Importar:
                      from ren_cfdi import CFDi
                      -Inicializar:
                      new_cfdi = CFDi(nombre_archivo_xml, prefijo)
                      - Renombrar archivo:
                      new_cfdi.rename_file()
                      - Generar línea de CSV
                      new_cfdi.generate_csv_line(nombre_archivo_csv)
'''
import sys
import os
import csv
from xml.dom import minidom

TAX_DICT = {
    '001': 'ISR',
    '002': 'IVA',
    '003': 'IEPS',
}

class CFDi(object):
    """
    Obtiene la información de un archivo XML para su renombrado.
    """
    fileName = ''
    comprobante = None
    docType = ''
    values = False

    def __init__(self, fileName, prefix=False):
        """
        Método constructor de la instancia.
        Recibe el nombre de un archivo XML y lo procesa para obtener sus
        atributos, cambiar el nombre e insertar algunos de sus valores en un CSV
        """
        self.fileName = fileName
        self.attributes = dict()
        self.prefix = prefix
        # Comprueba que el archivo exista
        if os.path.isfile(fileName):
            # Convierte el XML en un objeto MiniDOM para poder manipularlo
            self.comprobante = minidom.parse(fileName).childNodes[0]
        err = self.setAttributes()
        if err:
            raise ValueError('Error!.%s'% err)

        self.set_values_dict()
        self.set_name()

    def setAttributes(self):
        """
        Obtiene los atributos del archivo XML y los guarda en la variable attributes
        """

        if self.comprobante:
            self.attributes['comprobante'] = dict(self.comprobante.attributes.items())
            self.docType = self.attributes['comprobante'].get("TipoDeComprobante")
            errors = []
            errors.append(self.process_timbre())
            errors.append(self.process_emisor())
            errors.append(self.process_receptor())
            self.process_impuestos()
            errors.append(self.process_nomina())
            errors.append(self.process_pago())
            if any(errors):
                error = "\n".join([x for x in errors if x])
                return "Se encontraron los siguientes errores: \n{}\nEn {}".format(error, self.fileName)
            return False

        return "El CFDi no es válido: {}".format(self.fileName)


    def process_pago(self):
        """
        Obtiene los atributos del elemento pago10:Pagos
        y los adjunta al diccionario de atributos en caso de existir.
        """
        if self.docType == 'P':
            pagos = self.comprobante.getElementsByTagName('cfdi:Complemento')[0]\
                .getElementsByTagName('pago10:Pagos')[0]
            if not pagos:
                return "El CFDi no cuenta con Pagos"
            data = {}
            data['total'] = 0.0
            data['pagos'] = []

            for pag in pagos.getElementsByTagName('pago10:Pago'):
                pagoAttrs = dict(pag.attributes.items())
                pago = {}
                pago['monto'] = float(pagoAttrs.get('Monto', 0))
                pago['no'] = pagoAttrs.get('NumOperacion')
                pago['forma'] = pagoAttrs.get('FormaDePago')
                pago['fecha'] = pagoAttrs.get('FechaPago')
                pago['moneda'] = pagoAttrs.get('MonedaP')
                pago['doctos'] = []

                for doc in pag.getElementsByTagName('pago10:DoctoRelacionado'):
                    doctoAttrs = dict(doc.attributes.items())
                    docto = {}
                    importe = float(doctoAttrs.get('ImpPagado', 0))
                    docto['docto'] = doctoAttrs.get('IdDocumento')
                    docto['importe'] = importe
                    data['total'] += importe
                    pago['doctos'].append(docto)

                data['pagos'].append(pago)
            self.attributes['pago'] = data
        else:
            self.attributes['pago'] = False
        return False

    def process_nomina(self):
        """
        Obtiene los atributos del elemento nomina12:Nomina
        y los adjunta al diccionario de atributos en caso de existir.
        """
        if self.docType == 'N':
            nomina = self.comprobante.getElementsByTagName('cfdi:Complemento')[0]\
                .getElementsByTagName('nomina12:Nomina')[0]
            if not nomina:
                return "El CFDi no cuenta con Nómina"
            nominaAttrs = dict(nomina.attributes.items())
            data = {}
            data['version'] = nominaAttrs.get('Version')
            data['tipo'] = nominaAttrs.get('TipoNomina')
            data['total_p'] = nominaAttrs.get('TotalPercepciones', 0)
            data['total_d'] = nominaAttrs.get('TotalDeducciones', 0)
            data['total_o'] = nominaAttrs.get('TotalOtrosPagos', 0)

            # Procesa datos receptor
            receptor = nomina.getElementsByTagName('nomina12:Receptor')[0]
            recAttrs = dict(receptor.attributes.items())
            data['receptor'] = {
                'no_emp': recAttrs.get('NumEmpleado'),
                'curp': recAttrs.get('Curp'),
                'seguro': recAttrs.get('NumSeguridadSocial'),
                'sdi': recAttrs.get('SalarioDiarioIntegrado'),
            }

            # Procesar reglas salariales
            data['percepciones'] = []
            data['deducciones'] = []
            data['otros'] = []

            # Procesamiento de Percepciones
            for percepciones in nomina.getElementsByTagName('nomina12:Percepciones'):
                for percepcion in percepciones.getElementsByTagName('nomina12:Percepcion'):
                    perAttrs = dict(percepcion.attributes.items())
                    per = {}
                    per['tipo'] = perAttrs.get('TipoPercepcion')
                    per['clave'] = perAttrs.get('Clave')
                    per['monto'] = float(perAttrs.get('ImporteExento', 0)) + \
                        float(perAttrs.get('ImporteGravado', 0))
                    data['percepciones'].append(per)

            # Procesamiento de Deducciones
            for deducciones in nomina.getElementsByTagName('nomina12:Deducciones'):
                for deduccion in deducciones.getElementsByTagName('nomina12:Deduccion'):
                    dedAttrs = dict(deduccion.attributes.items())
                    ded = {}
                    ded['tipo'] = dedAttrs.get('TipoDeduccion')
                    ded['monto'] = float(dedAttrs.get('Importe', 0))
                    data['deducciones'].append(ded)

            # Procesamiento de Otros Pagos
            for otros in nomina.getElementsByTagName('nomina12:OtrosPagos'):
                for otro in otros.getElementsByTagName('nomina12:OtroPago'):
                    otroAttrs = dict(otro.attributes.items())
                    otro = {}
                    otro['tipo'] = otroAttrs.get('TipoOtroPago')
                    otro['monto'] = float(otroAttrs.get('Importe', 0))
                    data['otros'].append(otro)

            self.attributes['nomina'] = data
        else:
            self.attributes['nomina'] = False
        return False


    def process_impuestos_childs(self, impuestos, iType):
        """
        Procesa los elementos que componen al elemento Impuesto
        generando un diccionario de sus atributos
        """
        data = {}
        data['total'] = 0.0
        if iType == 'T':
            elements = impuestos.getElementsByTagName('cfdi:Traslados')
        elif iType == 'R':
            elements = impuestos.getElementsByTagName('cfdi:Retenciones')
        if not elements:
            return data
        for node in elements[0].childNodes:
            if node.__class__.__name__ == 'Element':
                nodeAttrs = dict(node.attributes.items())
                subTotal = float(nodeAttrs.get('Importe', 0))
                data['total'] += subTotal
                if data.get(nodeAttrs['Impuesto']):
                    data[nodeAttrs['Impuesto']] += subTotal
                else:
                    data[nodeAttrs['Impuesto']] = subTotal
        return data

    def process_impuestos(self):
        """
        Obtiene los atributos del elemento cfdi:Impuestos
        y los adjunta al diccionario de atributos en caso de existir.
        """
        impuestos = self.comprobante.getElementsByTagName('cfdi:Impuestos')
        if not impuestos:
            return False
        data = {}
        data['traslados'] = self.process_impuestos_childs(impuestos[0], 'T')
        data['retenciones'] =self.process_impuestos_childs(impuestos[0], 'R')
        self.attributes['impuestos'] = data
        return False

    def process_receptor(self):
        """
        Obtiene los atributos del elemento cfdi:Receptor
        y los adjunta al diccionario de atributos
        """
        receptor = self.comprobante.getElementsByTagName('cfdi:Receptor')
        if not receptor:
            return "El CFDi no cuenta con Receptor"
        data = {}
        data['rfc'] = receptor[0].getAttribute('Rfc')
        data['nombre'] = receptor[0].getAttribute('Nombre')
        data['uso_cfdi'] = receptor[0].getAttribute('UsoCFDI')
        self.attributes['receptor'] = data
        return False

    def process_emisor(self):
        """
        Obtiene los atributos del elemento cfdi:Emisor
        y los adjunta al diccionario de atributos
        """
        emisor = self.comprobante.getElementsByTagName('cfdi:Emisor')
        if not emisor:
            return "El CFDi no cuenta con Emisor"
        data = {}
        data['rfc'] = emisor[0].getAttribute('Rfc')
        data['nombre'] = emisor[0].getAttribute('Nombre')
        self.attributes['emisor'] = data
        return False

    def process_timbre(self):
        """
        Obtiene los atributos del elemento tfd:TimbreFiscalDigital
        y los adjunta al diccionario de atributos
        """
        tfd = self.comprobante.getElementsByTagName('tfd:TimbreFiscalDigital')
        if not tfd:
            return "El CFDi no cuenta con Timbre Fiscal Digital."
        self.attributes['timbre'] = dict(tfd[0].attributes.items())
        return False

    def get_pagos_data(self):
        """
        Devuelve los 4 ultimos dígitos del UUID y el monto total contenidos
        en el complemento de pago, si el CFDi no es de tipo 'P' devuelve
        valores genéricos de estos atributos.
        """
        uuid = 'XXXX'
        monto = '-'
        if self.docType == 'P':
            uuid = self.attributes['pago']['pagos'][0]['doctos'][0]['docto'][-4:]
            monto = 0.0
            for pago in self.attributes['pago']['pagos']:
                for docto in pago['doctos']:
                    monto += docto['importe']
        return uuid, monto

    # Filtrado de reglas salariales
    def get_per_data(self, percepciones):
        """
        Obtiene el total de percepciones en un CFDi de Nómina, filtra por clave para
        no sumar algunas claves (modificar a conveniencia del usuario final)
        """
        total_per = 0.0
        for per in percepciones:
            try:
                if int(per['clave']) < 15:
                    total_per += float(per['monto'])
            except:
                total_per += float(per['monto'])
        return total_per

    def get_ded_data(self, deducciones):
        """
        Obtiene el total de deducciones en un CFDi de Nómina, filtra por clave para
        no sumar algunas claves (modificar a conveniencia del usuario final)
        """
        total_ded = 0.0
        isr = 0.0
        deducciones_no_incluidas = ['080', '081']
        for ded in deducciones:
            if ded['tipo'] not in deducciones_no_incluidas:
                total_ded += float(ded['monto'])
            if ded['tipo'] == '002':
                isr += float(ded['monto'])
        return total_ded, isr

    def get_op_data(self, otros):
        """
        Obtiene el total de otros pagos en un CFDi de Nómina, filtra por clave para
        no sumar algunas claves (modificar a conveniencia del usuario final)
        """
        total_op = 0.0
        otros_no_incluidos = ['003', '999']
        for op in otros:
            if op['tipo'] not in otros_no_incluidos:
                total_op += float(op['monto'])
        return total_op

    def get_filtered_nomina_data(self):
        """
        Método que procesa la información de la nómina y la filtra
        (a petición del usuario final).
        Devuelve una Tupla con las siguientes variables:
        1. Percepciones filtradas                               (índice 0)
        2. Deducciones filtradas                                (índice 1)
        3. Otros Pagos filtrados                                (índice 2)
        4. Pago Neto en base a las reglas previamente filtradas (índice 3)
        5. ISR Deducido en el comprobante de nómina             (índice 4)
        """
        data = []
        nomina = self.attributes['nomina']
        if self.docType == 'N':
            data.append(self.get_per_data(nomina['percepciones']))
            ded, isr = self.get_ded_data(nomina['deducciones'])
            data.append(ded)
            data.append(self.get_op_data(nomina['otros']))
            data.append(float(data[0]) + float(data[2]) - float(data[1]))
            data.append(isr)
        else:
            data = ['-'] * 5
        return data

    def get_nomina_data(self):
        """
        Función que procesa la información de la nómina, devuelve los atributos
        del complemento de nómina sin hacer procesamiento especial.
        Devuelve una Tupla con las siguientes variables:
        1. Atributo TotalPercepciones           (índice 0)
        1. Atributo TotalOtrosPagos             (índice 1)
        1. Atributo TotalDeducciones            (índice 2)
        1. Pago neto en base a los atributos    (índice 3)
        1. Versión del complemento de Nómina    (índice 4)
        1. Número de empleado                   (índice 5)
        """
        data = []
        print self.docType
        if self.docType == 'N':
            data.append(self.attributes['nomina']['total_p'])
            data.append(self.attributes['nomina']['total_o'])
            data.append(self.attributes['nomina']['total_d'])
            data.append(float(data[0]) + float(data[1]) - float(data[2]))
            data.append(self.attributes['nomina']['version'])
            data.append(self.attributes['nomina']['receptor']['no_emp'])
        else:
            data = ['-'] * 6
        return data

    def set_values_dict(self):
        """
        Obtiene los valores que se utilizarán para generar el nombre del archivo
        así como el archivo csv con el resumen de las operaciones.
        Estos valores son almacenados en la variable values
        """
        values = {}
        values['tipo'] = self.docType
        values['uuid1'] = self.attributes['timbre'].get('UUID', 'XXXX')[-4:]
        values['rfce'] = self.attributes['emisor'].get('rfc', 'AAA010101AAA')[:-7]
        values['folio'] = self.attributes['comprobante'].get('Folio', 'NA')
        values['rfcr'] = self.attributes['receptor'].get('rfc', 'AAA010101AAA')[:-7]
        values['uso_cfdi'] = self.attributes['receptor'].get('uso_cfdi', 'NA')
        values['total'] = self.attributes['comprobante'].get('Total', 0)
        values['mpago'] = self.attributes['comprobante'].get('MetodoPago', '-')
        values['ver'] = self.attributes['comprobante'].get('Version', '-')
        uuid2, monto = self.get_pagos_data()
        values['uuid2'] = uuid2
        values['monto'] = monto
        nomina = self.get_nomina_data()
        values['nom_ver'] = nomina[4]
        values['per'] = nomina[0]
        values['op'] = nomina[1]
        values['ded'] = nomina[2]
        values['neto'] = nomina[3]
        values['no_emp'] = nomina[5]
        nomina_filt = self.get_filtered_nomina_data()
        values['per_f'] = nomina_filt[0]
        values['ded_f'] = nomina_filt[1]
        values['op_f'] = nomina_filt[2]
        values['neto_f'] = nomina_filt[3]
        values['ded_isr'] = nomina_filt[4]
        values['subtotal'] = self.attributes['comprobante'].get('SubTotal', '-')
        values['descuento'] = self.attributes['comprobante'].get('Descuento', 0)
        if self.attributes.get('impuestos'):
            values['traslados'] = self.attributes['impuestos']['traslados']['total']
            values['isr_t'] = self.attributes['impuestos']['traslados'].get('001', 0)
            values['iva_t'] = self.attributes['impuestos']['traslados'].get('002', 0)
            values['ieps_t'] = self.attributes['impuestos']['traslados'].get('003', 0)
            values['retenciones'] = self.attributes['impuestos']['retenciones']['total']
            values['isr_r'] = self.attributes['impuestos']['retenciones'].get('001', 0)
            values['iva_r'] = self.attributes['impuestos']['retenciones'].get('002', 0)
        else:
            values['traslados'] = 0
            values['isr_t'] = 0
            values['iva_t'] = 0
            values['ieps_t'] = 0
            values['retenciones'] = 0
            values['isr_r'] = 0
            values['iva_r'] = 0
        self.values = values

    def get_name_n(self, v, p):
        """
        Genera el nombre de archivo para los CFDi Tipo 'N' (nómina)
        """
        t = self.docType
        file_name = "{}-{}_{}_{}_{}_{}_{}_{}{}".format(p, v['uuid1'],
            v['rfcr'], v['no_emp'], v['rfce'], v['per_f'], v['neto_f'], t, v['nom_ver'])
        return file_name

    def get_name_i(self, v, p):
        """
        Genera el nombre de archivo para los CFDi que no sean tipo 'N' o 'P'
        pensado para soportar 'I' (ingreso) o 'E' (egreso).
        TODO: Probar 'T' (traslado)
        """
        t = self.docType
        file_name = "{}-{}_{}_{}_{}_{}_{}_{}_{}{}".format(p, v['uuid1'], \
            v['rfce'], v['folio'], v['rfcr'], v['total'], v['uso_cfdi'], v['mpago'], t, v['ver'])
        return file_name

    def get_name_p(self, v, p):
        """
        Genera el nombre de archivo para los CFDi Tipo 'P' (pago)
        """
        t = self.docType
        file_name = "{}-{}_{}_{}_{}_#{}_{}_{}{}".format(p, v['uuid1'], \
            v['rfce'], v['folio'], v['rfcr'], v['uuid2'], v['monto'], t, v['ver'])
        return file_name

    def set_name(self):
        """
        Obtiene el nuevo nombre de archivo dependiendo del tipo de CFDi.
        """
        prefix = 'T'
        if self.prefix:
            try:
                prefix = "T{}".format(int(self.prefix))
            except:
                prefix = self.prefix
        if self.docType == 'P':
            self.values['file_name'] = self.get_name_p(self.values, prefix)
        elif self.docType == 'N':
            self.values['file_name'] = self.get_name_n(self.values, prefix)
        else:
            self.values['file_name'] = self.get_name_i(self.values, prefix)

    def get_csv_line(self):
        """
        Genera una fila para CSV (verificar concordancia entre este método y
        el archivo CSV previamente generado)
        """
        line = []
        v = self.values
        line.append(str(v['file_name']))
        line.append(str(v['rfce']))
        line.append(str(v['rfcr']))
        line.append(str(v['uuid1']))
        line.append(str(v['folio']))
        line.append(str(v['subtotal']))
        line.append(str(v['descuento']))
        line.append(str(v['total']))
        line.append(str(v['traslados']))
        line.append(str(v['isr_t']))
        line.append(str(v['iva_t']))
        line.append(str(v['ieps_t']))
        line.append(str(v['retenciones']))
        line.append(str(v['isr_r']))
        line.append(str(v['iva_r']))
        line.append(str(v['per_f']))
        line.append(str(v['op_f']))
        line.append(str(v['ded_f']))
        line.append(str(v['ded_isr']))
        line.append(str(v['neto_f']))
        line.append(str(v['mpago']))
        line.append(str(v['tipo']))
        line.append(str(v['ver']))
        return ",".join(line)

    def rename_file(self):
        """
        Renombra el archivo XML con el formato obtenido en el método set_name()
        """
        newFileName = os.path.dirname(self.fileName)

        # Manipular Nombre Anterior
        oldFileName = os.path.splitext(self.fileName)
        # PDF y XML
        oldFileNameXml = "{}.xml".format(oldFileName[0])
        oldFileNamePdf = "{}.pdf".format(oldFileName[0])

        if len(newFileName) > 0:
            newFileName = "{}{}".format(newFileName, os.sep)
        newFileName = "{}{}".format(newFileName, self.values['file_name'])

        # Nuevos nombres de archivo PDF y XML
        newFileNamePdf = "{}.pdf".format(newFileName)
        newFileNameXml = "{}.xml".format(newFileName)

        # Comprobar que no existe el archivo XML con nombre nuevo para renombrar
        if not os.path.isfile(newFileNameXml):
            os.rename(oldFileNameXml, newFileNameXml)
            os.system("touch {}".format(newFileNameXml))

        # Comprobar que no exista el archivo PDF con nombre nuevo
        if not os.path.isfile(newFileNamePdf):
            # Comprobar que no exista un archivo PDF con el mismo nombre que el XML anterior
            if os.path.isfile(oldFileNamePdf):
                os.rename(oldFileNamePdf, newFileNamePdf)
                os.system("touch {}".format(newFileNamePdf))

        print "{} => {}".format(self.fileName, self.values['file_name'])

    def generate_csv_line(self, fileCsvName):
        """
        Genera línea de Archivo CSV
        """
        f = open(fileCsvName, 'a')
        lineCSV = self.get_csv_line()
        f.write("{}\n".format(lineCSV))
        f.close()
