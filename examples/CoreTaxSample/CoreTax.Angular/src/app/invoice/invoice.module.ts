import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterModule, Routes } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';

import { InvoiceComponent } from './invoice.component';
import { InvoiceService } from './invoice.service';

const routes: Routes = [
  {
    path: 'invoice',
    component: InvoiceComponent,
    data: { title: 'Tax Invoice (Faktur Pajak) - CoreTax DJP' }
  },
  {
    path: 'invoice/create',
    component: InvoiceComponent,
    data: { title: 'Create Invoice - CoreTax DJP', mode: 'create' }
  },
  {
    path: 'invoice/detail/:id',
    component: InvoiceComponent,
    data: { title: 'Invoice Detail - CoreTax DJP', mode: 'detail' }
  }
];

@NgModule({
  declarations: [
    InvoiceComponent
  ],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    HttpClientModule,
    RouterModule.forChild(routes)
  ],
  providers: [
    InvoiceService
  ],
  exports: [
    InvoiceComponent
  ]
})
export class InvoiceModule {}
