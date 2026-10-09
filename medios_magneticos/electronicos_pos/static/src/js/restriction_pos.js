odoo.define('electronicos_pos.PaymentScreenExtension', function(require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PaymentScreenExtension = PaymentScreen => class extends PaymentScreen {
        async validateOrder(isForceValidate) {
            let order = this.env.pos.get_order();
            let uvtValue = this.env.pos.config.valor_uvt;
			var self = this;
			console.log(this.env.pos.config);
            console.log(uvtValue);
            if ( order.is_to_invoice() && order.get_total_with_tax()-order.get_total_tax() > uvtValue ) {
                
					self.showPopup('ErrorPopup', {
						title: "No se puede generar Documento equivalente POS.",
						body: "Hola, Te recordamos que, de acuerdo con las normativas tributarias, estás obligado a emitir factura electrónica después de haber alcanzado el monto de 5 UVTs, lo cual equivale a $212.060. Por lo tanto, completa la operación correspondiente utilizando una factura electrónica. ___________________________________________________________ Obten mas informacion en el siguiente enlace https://www.navegasoft.com/forum/centro-de-ayuda-2/configura-tu-sistema-pos-para-ventas-superiores-a-5-uvt-colombia-204   ___________________________________________________________ Desmarca la opcion factura para poder continuar. ",
					});
                return;
            }
            return super.validateOrder(isForceValidate);
        }
    };

    Registries.Component.extend(PaymentScreen, PaymentScreenExtension);

    return PaymentScreen;
});