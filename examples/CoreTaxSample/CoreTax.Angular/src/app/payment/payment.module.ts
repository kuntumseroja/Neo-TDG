import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterModule, Routes } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';

import { PaymentComponent } from './payment.component';
import { PaymentService } from './payment.service';

const routes: Routes = [
  {
    path: 'payment',
    component: PaymentComponent,
    data: { title: 'Tax Payment - CoreTax DJP' }
  },
  {
    path: 'payment/billing',
    component: PaymentComponent,
    data: { title: 'Generate Billing Code - CoreTax DJP', mode: 'billing' }
  },
  {
    path: 'payment/detail/:id',
    component: PaymentComponent,
    data: { title: 'Payment Detail - CoreTax DJP', mode: 'detail' }
  }
];

@NgModule({
  declarations: [
    PaymentComponent
  ],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    HttpClientModule,
    RouterModule.forChild(routes)
  ],
  providers: [
    PaymentService
  ],
  exports: [
    PaymentComponent
  ]
})
export class PaymentModule {}
