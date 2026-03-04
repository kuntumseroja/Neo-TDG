import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { FilingService, TaxFilingRequest, TaxFilingResponse } from './filing.service';

@Component({
  selector: 'app-filing',
  templateUrl: './filing.component.html',
  styleUrls: ['./filing.component.scss']
})
export class FilingComponent implements OnInit {
  filingForm!: FormGroup;
  filingResult: TaxFilingResponse | null = null;
  filingList: TaxFilingResponse[] = [];
  isLoading = false;
  errorMessage: string | null = null;
  activeTab: 'create' | 'list' | 'detail' = 'create';
  selectedFiling: TaxFilingResponse | null = null;

  filingTypes = [
    { value: 'SPT_MASA_PPN', label: 'SPT Masa PPN' },
    { value: 'SPT_MASA_PPH_21', label: 'SPT Masa PPh Pasal 21' },
    { value: 'SPT_MASA_PPH_23', label: 'SPT Masa PPh Pasal 23' },
    { value: 'SPT_MASA_PPH_4_2', label: 'SPT Masa PPh Pasal 4 Ayat 2' },
    { value: 'SPT_TAHUNAN_OP', label: 'SPT Tahunan Orang Pribadi' },
    { value: 'SPT_TAHUNAN_BADAN', label: 'SPT Tahunan Badan' }
  ];

  taxPeriods: string[] = [];
  taxYears: number[] = [];

  constructor(
    private fb: FormBuilder,
    private filingService: FilingService
  ) {}

  ngOnInit(): void {
    this.initForm();
    this.generatePeriods();
    this.loadFilings();
  }

  private initForm(): void {
    this.filingForm = this.fb.group({
      npwp: ['', [Validators.required, Validators.pattern(/^\d{15,16}$/)]],
      filingType: ['SPT_MASA_PPN', [Validators.required]],
      taxPeriod: ['', [Validators.required]],
      taxYear: [new Date().getFullYear(), [Validators.required]],
      grossIncome: [0, [Validators.required, Validators.min(0)]],
      taxableIncome: [0, [Validators.required, Validators.min(0)]],
      taxDue: [0, [Validators.required, Validators.min(0)]],
      taxPaid: [0, [Validators.required, Validators.min(0)]],
      taxOverpaid: [0],
      taxUnderpaid: [0],
      isAmendment: [false],
      amendmentNumber: [0]
    });
  }

  private generatePeriods(): void {
    this.taxPeriods = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];

    const currentYear = new Date().getFullYear();
    this.taxYears = Array.from({ length: 5 }, (_, i) => currentYear - i);
  }

  calculateTaxBalance(): void {
    const taxDue = this.filingForm.get('taxDue')?.value || 0;
    const taxPaid = this.filingForm.get('taxPaid')?.value || 0;
    const balance = taxPaid - taxDue;

    if (balance > 0) {
      this.filingForm.patchValue({ taxOverpaid: balance, taxUnderpaid: 0 });
    } else if (balance < 0) {
      this.filingForm.patchValue({ taxOverpaid: 0, taxUnderpaid: Math.abs(balance) });
    } else {
      this.filingForm.patchValue({ taxOverpaid: 0, taxUnderpaid: 0 });
    }
  }

  onSubmitFiling(): void {
    if (this.filingForm.invalid) {
      this.filingForm.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    this.errorMessage = null;

    const request: TaxFilingRequest = this.filingForm.value;

    this.filingService.submitFiling(request).subscribe({
      next: (response) => {
        this.filingResult = response;
        this.isLoading = false;
        this.loadFilings();
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Filing submission failed. Please try again.';
        this.isLoading = false;
      }
    });
  }

  loadFilings(): void {
    this.filingService.getFilings().subscribe({
      next: (filings) => {
        this.filingList = filings;
      },
      error: (error) => {
        console.error('Failed to load filings:', error);
      }
    });
  }

  viewFilingDetail(filingId: string): void {
    this.filingService.getFilingById(filingId).subscribe({
      next: (filing) => {
        this.selectedFiling = filing;
        this.activeTab = 'detail';
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Failed to load filing details.';
      }
    });
  }

  downloadReceipt(filingId: string): void {
    this.filingService.downloadFilingReceipt(filingId).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `filing-receipt-${filingId}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (error) => {
        this.errorMessage = 'Failed to download receipt.';
      }
    });
  }

  setActiveTab(tab: 'create' | 'list' | 'detail'): void {
    this.activeTab = tab;
    this.errorMessage = null;
  }

  resetForm(): void {
    this.filingForm.reset({
      filingType: 'SPT_MASA_PPN',
      taxYear: new Date().getFullYear(),
      grossIncome: 0,
      taxableIncome: 0,
      taxDue: 0,
      taxPaid: 0,
      taxOverpaid: 0,
      taxUnderpaid: 0,
      isAmendment: false,
      amendmentNumber: 0
    });
    this.filingResult = null;
    this.errorMessage = null;
  }
}
