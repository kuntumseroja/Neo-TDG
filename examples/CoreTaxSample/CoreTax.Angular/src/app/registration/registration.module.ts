import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterModule, Routes } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';

import { RegistrationComponent } from './registration.component';
import { RegistrationService } from './registration.service';

const routes: Routes = [
  {
    path: 'registration',
    component: RegistrationComponent,
    data: { title: 'Tax Registration - CoreTax DJP' }
  },
  {
    path: 'registration/status/:npwp',
    component: RegistrationComponent,
    data: { title: 'Registration Status - CoreTax DJP' }
  }
];

@NgModule({
  declarations: [
    RegistrationComponent
  ],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    HttpClientModule,
    RouterModule.forChild(routes)
  ],
  providers: [
    RegistrationService
  ],
  exports: [
    RegistrationComponent
  ]
})
export class RegistrationModule {}
