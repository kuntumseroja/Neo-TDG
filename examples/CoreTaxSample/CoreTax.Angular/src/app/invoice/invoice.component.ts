import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { InvoiceService, InvoiceSubmitRequest, InvoiceResponse, InvoiceLineItem } from './invoice.service';

@Component({
  selector: 'app-invoice',
  templateUrl: './invoice.component.html',
  styleUrls: ['./invoice.component.scss']
})
export class InvoiceComponent implements OnInit {
  invoiceForm!: FormGroup;
  invoiceResult: InvoiceResponse | null = null;
  invoiceList: InvoiceResponse[] = [];
  isLoading = false;
  errorMessage: string | null = null;
  activeTab: 'create' | 'list' | 'detail' = 'create';
  selectedInvoice: InvoiceResponse | null = null;

  invoiceTypes = [
    { value: 'STANDARD', label: 'Faktur Pajak Standar' },
    { value: 'COMBINED', label: 'Faktur Pajak Gabungan' },
    { value: 'REPLACEMENT', label: 'Faktur Pajak Pengganti' },
    { value: 'CANCELED', label: 'Faktur Pajak Batal' }
  ];

  taxCodes = [
    { value: '010', label: '010 - PPN 11%' },
    { value: '020', label: '020 - PPN Dipungut Bendahara' },
    { value: '030', label: '030 - PPN Tidak Dipungut' },
    { value: '040', label: '040 - PPN Dibebaskan' },
    { value: '070', label: '070 - PPN Tidak Dikenakan' },
    { value: '080', label: '080 - PPN Dibebaskan (BKP Tertentu)' }
  ];

  constructor(
    private fb: FormBuilder,
    private invoiceService: InvoiceService
  ) {}

  ngOnInit(): void {
    this.initForm();
    this.loadInvoices();
  }

  private initForm(): void {
    this.invoiceForm = this.fb.group({
      sellerNpwp: ['', [Validators.required, Validators.pattern(/^\d{15,16}$/)]],
      sellerName: ['', [Validators.required]],
      buyerNpwp: ['', [Validators.required, Validators.pattern(/^\d{15,16}$/)]],
      buyerName: ['', [Validators.required]],
      invoiceType: ['STANDARD', [Validators.required]],
      taxCode: ['010', [Validators.required]],
      transactionDate: ['', [Validators.required]],
      description: [''],
      lineItems: this.fb.array([this.createLineItem()])
    });
  }

  private createLineItem(): FormGroup {
    return this.fb.group({
      itemName: ['', [Validators.required]],
      quantity: [1, [Validators.required, Validators.min(1)]],
      unitPrice: [0, [Validators.required, Validators.min(0)]],
      discount: [0, [Validators.min(0)]],
      taxRate: [11, [Validators.required, Validators.min(0), Validators.max(100)]]
    });
  }

  get lineItems(): FormArray {
    return this.invoiceForm.get('lineItems') as FormArray;
  }

  addLineItem(): void {
    this.lineItems.push(this.createLineItem());
  }

  removeLineItem(index: number): void {
    if (this.lineItems.length > 1) {
      this.lineItems.removeAt(index);
    }
  }

  calculateSubtotal(): number {
    return this.lineItems.controls.reduce((sum, item) => {
      const qty = item.get('quantity')?.value || 0;
      const price = item.get('unitPrice')?.value || 0;
      const discount = item.get('discount')?.value || 0;
      return sum + (qty * price) - discount;
    }, 0);
  }

  calculateTotalTax(): number {
    return this.lineItems.controls.reduce((sum, item) => {
      const qty = item.get('quantity')?.value || 0;
      const price = item.get('unitPrice')?.value || 0;
      const discount = item.get('discount')?.value || 0;
      const taxRate = item.get('taxRate')?.value || 0;
      const lineTotal = (qty * price) - discount;
      return sum + (lineTotal * taxRate / 100);
    }, 0);
  }

  onSubmitInvoice(): void {
    if (this.invoiceForm.invalid) {
      this.invoiceForm.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    this.errorMessage = null;

    const formValue = this.invoiceForm.value;
    const request: InvoiceSubmitRequest = {
      sellerNpwp: formValue.sellerNpwp,
      sellerName: formValue.sellerName,
      buyerNpwp: formValue.buyerNpwp,
      buyerName: formValue.buyerName,
      invoiceType: formValue.invoiceType,
      taxCode: formValue.taxCode,
      transactionDate: formValue.transactionDate,
      description: formValue.description,
      lineItems: formValue.lineItems.map((item: any) => ({
        itemName: item.itemName,
        quantity: item.quantity,
        unitPrice: item.unitPrice,
        discount: item.discount,
        taxRate: item.taxRate
      }))
    };

    this.invoiceService.submitInvoice(request).subscribe({
      next: (response) => {
        this.invoiceResult = response;
        this.isLoading = false;
        this.loadInvoices();
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Invoice submission failed. Please try again.';
        this.isLoading = false;
      }
    });
  }

  loadInvoices(): void {
    this.invoiceService.getInvoices().subscribe({
      next: (invoices) => {
        this.invoiceList = invoices;
      },
      error: (error) => {
        console.error('Failed to load invoices:', error);
      }
    });
  }

  viewInvoiceDetail(invoiceId: string): void {
    this.invoiceService.getInvoiceById(invoiceId).subscribe({
      next: (invoice) => {
        this.selectedInvoice = invoice;
        this.activeTab = 'detail';
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Failed to load invoice details.';
      }
    });
  }

  cancelInvoice(invoiceId: string): void {
    if (!confirm('Are you sure you want to cancel this invoice?')) return;

    this.invoiceService.cancelInvoice(invoiceId).subscribe({
      next: () => {
        this.loadInvoices();
        this.selectedInvoice = null;
        this.activeTab = 'list';
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Failed to cancel invoice.';
      }
    });
  }

  setActiveTab(tab: 'create' | 'list' | 'detail'): void {
    this.activeTab = tab;
    this.errorMessage = null;
  }

  resetForm(): void {
    this.invoiceForm.reset({ invoiceType: 'STANDARD', taxCode: '010' });
    this.lineItems.clear();
    this.lineItems.push(this.createLineItem());
    this.invoiceResult = null;
    this.errorMessage = null;
  }
}
