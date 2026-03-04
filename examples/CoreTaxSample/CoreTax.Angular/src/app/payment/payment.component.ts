import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { PaymentService, TaxPaymentRequest, TaxPaymentResponse } from './payment.service';

@Component({
  selector: 'app-payment',
  templateUrl: './payment.component.html',
  styleUrls: ['./payment.component.scss']
})
export class PaymentComponent implements OnInit {
  paymentForm!: FormGroup;
  paymentResult: TaxPaymentResponse | null = null;
  paymentList: TaxPaymentResponse[] = [];
  isLoading = false;
  errorMessage: string | null = null;
  activeTab: 'create' | 'list' | 'detail' = 'create';
  selectedPayment: TaxPaymentResponse | null = null;
  billingCode: string | null = null;

  taxTypes = [
    { value: 'PPH_21', label: 'PPh Pasal 21' },
    { value: 'PPH_23', label: 'PPh Pasal 23' },
    { value: 'PPH_4_2', label: 'PPh Pasal 4 Ayat 2' },
    { value: 'PPH_25', label: 'PPh Pasal 25' },
    { value: 'PPH_29', label: 'PPh Pasal 29' },
    { value: 'PPN', label: 'PPN Dalam Negeri' },
    { value: 'PPN_IMPORT', label: 'PPN Impor' },
    { value: 'PPnBM', label: 'PPnBM' }
  ];

  depositTypes = [
    { value: '100', label: '100 - Masa' },
    { value: '200', label: '200 - Tahunan' },
    { value: '300', label: '300 - STP' },
    { value: '310', label: '310 - SKPKB' },
    { value: '320', label: '320 - SKPKBT' },
    { value: '500', label: '500 - Ketetapan Pajak Lainnya' }
  ];

  paymentMethods = [
    { value: 'BANK_TRANSFER', label: 'Transfer Bank' },
    { value: 'VIRTUAL_ACCOUNT', label: 'Virtual Account' },
    { value: 'E_BILLING', label: 'e-Billing (MPN G3)' },
    { value: 'COUNTER', label: 'Teller Bank/Pos' }
  ];

  constructor(
    private fb: FormBuilder,
    private paymentService: PaymentService
  ) {}

  ngOnInit(): void {
    this.initForm();
    this.loadPayments();
  }

  private initForm(): void {
    this.paymentForm = this.fb.group({
      npwp: ['', [Validators.required, Validators.pattern(/^\d{15,16}$/)]],
      taxType: ['PPN', [Validators.required]],
      depositType: ['100', [Validators.required]],
      taxPeriodMonth: ['', [Validators.required]],
      taxPeriodYear: [new Date().getFullYear(), [Validators.required]],
      amount: [0, [Validators.required, Validators.min(1)]],
      paymentMethod: ['E_BILLING', [Validators.required]],
      description: [''],
      filingId: ['']
    });
  }

  onGenerateBillingCode(): void {
    if (this.paymentForm.invalid) {
      this.paymentForm.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    this.errorMessage = null;

    const request: TaxPaymentRequest = this.paymentForm.value;

    this.paymentService.generateBillingCode(request).subscribe({
      next: (response) => {
        this.billingCode = response.billingCode;
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Failed to generate billing code.';
        this.isLoading = false;
      }
    });
  }

  onSubmitPayment(): void {
    if (!this.billingCode) {
      this.errorMessage = 'Please generate a billing code first.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = null;

    const request: TaxPaymentRequest = {
      ...this.paymentForm.value,
      billingCode: this.billingCode
    };

    this.paymentService.submitPayment(request).subscribe({
      next: (response) => {
        this.paymentResult = response;
        this.isLoading = false;
        this.loadPayments();
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Payment submission failed. Please try again.';
        this.isLoading = false;
      }
    });
  }

  loadPayments(): void {
    this.paymentService.getPayments().subscribe({
      next: (payments) => {
        this.paymentList = payments;
      },
      error: (error) => {
        console.error('Failed to load payments:', error);
      }
    });
  }

  viewPaymentDetail(paymentId: string): void {
    this.paymentService.getPaymentById(paymentId).subscribe({
      next: (payment) => {
        this.selectedPayment = payment;
        this.activeTab = 'detail';
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Failed to load payment details.';
      }
    });
  }

  verifyPayment(billingCode: string): void {
    this.paymentService.verifyPayment(billingCode).subscribe({
      next: (response) => {
        this.selectedPayment = response;
        this.activeTab = 'detail';
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Payment verification failed.';
      }
    });
  }

  downloadReceipt(paymentId: string): void {
    this.paymentService.downloadPaymentReceipt(paymentId).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `payment-receipt-${paymentId}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: () => {
        this.errorMessage = 'Failed to download receipt.';
      }
    });
  }

  setActiveTab(tab: 'create' | 'list' | 'detail'): void {
    this.activeTab = tab;
    this.errorMessage = null;
  }

  resetForm(): void {
    this.paymentForm.reset({
      taxType: 'PPN',
      depositType: '100',
      taxPeriodYear: new Date().getFullYear(),
      amount: 0,
      paymentMethod: 'E_BILLING'
    });
    this.paymentResult = null;
    this.billingCode = null;
    this.errorMessage = null;
  }
}
