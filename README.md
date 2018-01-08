[![Build Status](https://travis-ci.org/JayVora-SerpentCS/Jasperv8.svg?branch=master)](https://travis-ci.org/JayVora-SerpentCS/Jasperv8)
[![Build Status](https://travis-ci.org/JayVora-SerpentCS/Jasperv8.svg?branch=8.0)](https://travis-ci.org/JayVora-SerpentCS/Jasperv8)
========

This is the reopository for Jasper Reports in Odoo

Source : https://launchpad.net/openobject-jasper-reports

#
Fork for implement properties:
------------------------------
*  \<property name="OPENERP_MODULE"/>
*  \<property name="OPENERP_DYNAMIC"/>


>this allows executing functions to obtain the value of the field or generate the data to be displayed in the report

```

The examples are in 'report_samples' for model account.invoice.
Copy the *.py to jasper_reports/report/dynamic_modules and install
(like any other jasper report): 
- invoice.jrxml+invoice_sub.jrxml   -> normal
- invoicef.jrxml+invoicef_sub.jrxml -> width functions like fields
- invoiced.jrxml+invoiced_sub.jrxml -> generate data

```