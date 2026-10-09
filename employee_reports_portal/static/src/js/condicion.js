'use strict';
odoo.define('employee_reports_portal.condicion',['web.ajax'], function(require) {
    require('web.dom_ready');

    var start = document.getElementById('start');
    var end = document.getElementById('end');
    var duration = document.getElementById('duration');

    // Función para calcular la duración
    function calculateDuration() {
        var startHour = parseInt(start.value);
        var endHour = parseInt(end.value);
        
        // if (endHour < startHour) {
        //     alert('La hora final no puede ser menor que la hora inicial.');
        //     start.value = end.value = '';  // Restablecer los campos de selección
        //     duration.value = '';
        //     return;
        //   }
        
          var durationHour = endHour - startHour;
          duration.value = durationHour + ' horas';
    }

    // Agregar listeners a los eventos de cambio
    start.addEventListener('change', calculateDuration);
    end.addEventListener('change', calculateDuration);


    var ajax = require('web.ajax');

    var button = $('#boton');
    var _onchange = function(e) {
        
        ajax.jsonRpc('/get_condicion','call',{'tipos_input' : $( "#tipos_input" ).val(),}).then(function(data) {
            
            console.log(data[0]);
            // alert( "Handler for .change() called." );
            $("#condicion").text(data[0]) 
            
            console.log(data[1])
            if (data[1] == true){
                
                $("#mostrar_tratamiento").show();
            }else {
                $("#mostrar_tratamiento").hide(); 
            }
        })
    }
    

    var _onchange_mostar_horas = function(e) {
        if ($( "#mostrar_horas" ).val() == "SI"){
            $("#solo_horas").show();
        }else{
            $("#solo_horas").hide();
        }
    }

    var _onButton = function(e) {        

        if ($( "#tratamiento_datos" ).val() == "SI"){
            var tratamiento_datos = true
        }else{
            var tratamiento_datos = false
        }
        if ($( "#mostrar_horas" ).val() == "SI"){
        var start = document.getElementById('start');
        var end = document.getElementById('end');
        var startHour = parseInt(start.value);
        var endHour = parseInt(end.value);
        var durationHour = endHour - startHour;

        diccionario = {
            "holiday_status_id":$( "#tipos_input" ).val(),
            "request_date_from":$( "#from_date" ).val(),
            "request_date_to":$( "#to_date" ).val(),
            "name":$( "#descripcion" ).val(),
            "tratamiento_datos":tratamiento_datos,
            "request_unit_hours":true,
            "request_hour_from":start.value,
            "request_hour_to":end.value,
            "number_of_days_display":durationHour,
            "duration_display":durationHour,
        }

    }else{
        
        diccionario = {
            "holiday_status_id":$( "#tipos_input" ).val(),
            "request_date_from":$( "#from_date" ).val(),
            "request_date_to":$( "#to_date" ).val(),
            "name":$( "#descripcion" ).val(),
            "tratamiento_datos":tratamiento_datos,
            "request_unit_hours":false,
            "request_hour_from":0,
            "request_hour_to":0,
            "number_of_days_display":0,
            "duration_display":0,
        }

    }
        file = $( "#attach_pagina" ).prop('files')[0];  
        if (file) {
            nombre_file = file.name
            var image_input = null;
            console.log("reader")
            var reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = function(e)
              
            {
                    image_input = e.target.result;
                    var base64result = image_input.split(',')[1];
                    
                    // console.log(base64result)
                    //    console.log(image_input)
                        //console.log(base64result)
                        // console.log($( "#attach_pagina" ).prop('files')[0])
                        // console.log("image_input")
                        // console.log(image_input)
                    // $("#mensaje").text("Guardando el registro") 
                    //     setTimeout( function(){ 
                    //         console.log(diccionario)
                    //         console.log("no se salva");
                    //         $("#mensaje").text("Un momento se esta guardando el registro");
                    //     }  , 5000 );
                                                                                        //base64result
                    ajax.jsonRpc('/save_leave','call',{'diccionario' : diccionario,'file':image_input,'nombre_file':nombre_file}).then(function(data) {
                        
                        console.log("salvado");
                        // var form_data = new FormData();
                        // form_data.append('file', $('#uploadfile').prop('files')[0]);
                        // $.ajax({
                        //     type: 'POST',
                        //     url: '/uploadLabel',
                        //     data: form_data,
                        //     contentType: false,
                        //     cache: false,
                        //     processData: false,
                        //     success: function(data) {
                        //         console.log('Success!');
                        //     },
                        // });
                        location.reload();
                        // alert( "Handler for .change() called." );   
                    })
                    .catch(function (error) {
                        $("#mensaje").text('No se puede guardar la ausencia: '+ error.message.data.message); 
                        //error.message.data.message
                        console.error('Error occurred:', error.message.data.message);
                        // Aquí puedes mostrar un mensaje de error al usuario, por ejemplo:
                        // alert('Error occurred: ' + error.message);
                    });
                }
            }else{
                nombre_file = ""
                var image_input = "";
                
                // $("#mensaje").text("Guardando el registro") 
                //     setTimeout( function(){ 
                //         console.log(diccionario)
                //         console.log("no se salva");
                //         if (obligatorio){
                //             $("#mensaje").text("El adjunto es obligatorio para registrar tu solicitud"); 
                //         }else{
                //             $("#mensaje").text("No se puede guardar el registro, por que tienes conflictos en la fecha del permiso ");
                //         } 
                       
                //     }  , 5000 );

                ajax.jsonRpc('/save_leave', 'call', { 'diccionario': diccionario, 'file': image_input, 'nombre_file': nombre_file })
                .then(function (data) {
                    console.log(data);
                    location.reload();
                })
                .catch(function (error) {
                    $("#mensaje").text('No se puede guardar la ausencia: '+ error.message.data.message);
                    //error.message.data.message
                    console.error('Error occurred:', error.message.data.message);
                    // Aquí puedes mostrar un mensaje de error al usuario, por ejemplo:
                    // alert('Error occurred: ' + error.message);
                });

            }  
            
    }
    $("#solo_horas").hide();
    $("#tipos_input").change(function() {
        _onchange();
    });

    $("#mostrar_horas").change(function() {
        _onchange_mostar_horas();
    });

    button.click(_onButton);
    
})