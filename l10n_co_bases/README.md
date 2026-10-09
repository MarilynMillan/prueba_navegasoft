# l10n_co_bases
El modulo es compatible con la funcion de multi compañia de Odoo

La informacion que es importada corresponde a las definidas por la DIAN en el anexo tecnico Anexo técnico Estructura UBL y Validaciones Factura Electrónica 2.1 Versión 2 RESOLUCION (000001) DE 2019 https://www.dian.gov.co/fizcalizacioncontrol/herramienconsulta/FacturaElectronica/InformacionTecnica/Documents/Anexos_Tecnicos_v1_0.pdf:

    - Los grupos de impuestos se crean y estan disponibles para todas las compañias.

    - Se agregan los grupos de impuestos a la plantila de los impuestos que vienen cargados desde el modulo de contabilidad l10n_co.

    - Se desactivan impuestos desde la plantilla cargada desde el modulo de contabilidad l10n_co los cuales no estan listados dentro del anexo tecnico de la DIAN.

    - Se importan los estados(Municipios o ciudades) de Colombia, no se discriminan por departamento, cada estado se crea y dentro del mismo nombre se especifica a que Departamento pertenece.

    - Codigos postales en Estados, lo que se hizo para esta fue seleccionar un codigo postal aleatorio de cada estado y asignarlo a cada uno (Esta seccion de la importacion puede ser manejado de otra forma dependiendo de lo que se necesite)
    

Estructura de las tablas:

    - account.invoice(Facturacion) se adicionan algunos campos para ser compatible con el modulo num_to_words (Componente no validado, esto es suceptible a errores)

    - En res_country_state se agrega el campo para poder agregar el codigo postal el cual es obligatorio segun la DIAN para la facturacion electronica

    - res.partner se adicionan varios campos
        - Campos para manejar nombres y apellidos
        - Campos para NIT, digito de verificacion, tipo de identificacion y tipo de regimen
    
    - res.partner se adicionan varias funciones
        - Se modifica el name_search
        - Algunas funciones para validar el digito de verificacion y el NIT
        - Validacion para el NIT

