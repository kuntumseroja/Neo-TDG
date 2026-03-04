import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterModule, Routes } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';

import { FilingComponent } from './filing.component';
import { FilingService } from './filing.service';

const routes: Routes = [
  {
    path: 'filing',
    component: FilingComponent,
    data: { title: 'Tax Filing (SPT) - CoreTax DJP' }
  },
  {
    path: 'filing/create',
    component: FilingComponent,
    data: { title: 'Create Filing - CoreTax DJP', mode: 'create' }
  },
  {
    path: 'filing/detail/:id',
    component: FilingComponent,
    data: { title: 'Filing Detail - CoreTax DJP', mode: 'detail' }
  }
];

@NgModule({
  declarations: [
    FilingComponent
  ],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    HttpClientModule,
    RouterModule.forChild(routes)
  ],
  providers: [
    FilingService
  ],
  exports: [
    FilingComponent
  ]
})
export class FilingModule {}
