import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { RegistrationService } from './registration.service';

export interface TaxRegistrationRequest {
  taxpayerName: string;
  npwp: string;
  idNumber: string;
  idType: string;
  address: string;
  businessType: string;
  email: string;
  phone: string;
}

export interface TaxRegistrationResponse {
  registrationId: string;
  npwp: string;
  status: string;
  registeredDate: string;
  taxpayerName: string;
  message: string;
}

@Component({
  selector: 'app-registration',
  templateUrl: './registration.component.html',
  styleUrls: ['./registration.component.scss']
})
export class RegistrationComponent implements OnInit {
  registrationForm!: FormGroup;
  registrationResult: TaxRegistrationResponse | null = null;
  registrationStatus: string | null = null;
  isLoading = false;
  errorMessage: string | null = null;

  idTypes = [
    { value: 'KTP', label: 'KTP (Kartu Tanda Penduduk)' },
    { value: 'PASSPORT', label: 'Passport' },
    { value: 'KITAS', label: 'KITAS' }
  ];

  businessTypes = [
    { value: 'INDIVIDUAL', label: 'Orang Pribadi' },
    { value: 'CORPORATE', label: 'Badan Usaha' },
    { value: 'GOVERNMENT', label: 'Instansi Pemerintah' }
  ];

  constructor(
    private fb: FormBuilder,
    private registrationService: RegistrationService
  ) {}

  ngOnInit(): void {
    this.initForm();
  }

  private initForm(): void {
    this.registrationForm = this.fb.group({
      taxpayerName: ['', [Validators.required, Validators.minLength(3)]],
      npwp: ['', [Validators.required, Validators.pattern(/^\d{15,16}$/)]],
      idNumber: ['', [Validators.required]],
      idType: ['KTP', [Validators.required]],
      address: ['', [Validators.required, Validators.minLength(10)]],
      businessType: ['INDIVIDUAL', [Validators.required]],
      email: ['', [Validators.required, Validators.email]],
      phone: ['', [Validators.required, Validators.pattern(/^\+?[\d\-\s]{10,15}$/)]]
    });
  }

  onSubmitRegistration(): void {
    if (this.registrationForm.invalid) {
      this.registrationForm.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    this.errorMessage = null;

    const request: TaxRegistrationRequest = this.registrationForm.value;

    this.registrationService.registerTaxpayer(request).subscribe({
      next: (response) => {
        this.registrationResult = response;
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Registration failed. Please try again.';
        this.isLoading = false;
      }
    });
  }

  onCheckStatus(npwp: string): void {
    if (!npwp) return;

    this.isLoading = true;
    this.registrationService.getRegistrationStatus(npwp).subscribe({
      next: (response) => {
        this.registrationStatus = response.status;
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Failed to check status.';
        this.isLoading = false;
      }
    });
  }

  onValidateNpwp(): void {
    const npwp = this.registrationForm.get('npwp')?.value;
    if (!npwp) return;

    this.registrationService.validateNpwp(npwp).subscribe({
      next: (response) => {
        if (!response.isValid) {
          this.registrationForm.get('npwp')?.setErrors({ invalidNpwp: true });
        }
      },
      error: () => {
        // Validation endpoint unavailable, allow form submission
      }
    });
  }

  resetForm(): void {
    this.registrationForm.reset({ idType: 'KTP', businessType: 'INDIVIDUAL' });
    this.registrationResult = null;
    this.registrationStatus = null;
    this.errorMessage = null;
  }
}
