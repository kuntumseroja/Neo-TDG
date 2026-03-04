import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface TaxPaymentRequest {
  npwp: string;
  taxType: string;
  depositType: string;
  taxPeriodMonth: string;
  taxPeriodYear: number;
  amount: number;
  paymentMethod: string;
  description: string;
  filingId?: string;
  billingCode?: string;
}

export interface TaxPaymentResponse {
  paymentId: string;
  npwp: string;
  billingCode: string;
  taxType: string;
  depositType: string;
  taxPeriodMonth: string;
  taxPeriodYear: number;
  amount: number;
  paymentMethod: string;
  status: string;
  paymentDate: string;
  ntpn: string;
  receiptNumber: string;
  description: string;
}

export interface BillingCodeResponse {
  billingCode: string;
  npwp: string;
  amount: number;
  expiryDate: string;
  taxType: string;
  depositType: string;
}

@Injectable({
  providedIn: 'root'
})
export class PaymentService {
  private readonly apiUrl = `${environment.apiBaseUrl}/api/v1/taxpayment`;

  private httpOptions = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    })
  };

  constructor(private http: HttpClient) {}

  /**
   * Generate a billing code (Kode Billing) for tax payment via MPN G3.
   * POST /api/v1/taxpayment/billing
   */
  generateBillingCode(request: TaxPaymentRequest): Observable<BillingCodeResponse> {
    return this.http.post<BillingCodeResponse>(
      `${this.apiUrl}/billing`,
      request,
      this.httpOptions
    );
  }

  /**
   * Submit a tax payment with a valid billing code.
   * POST /api/v1/taxpayment/pay
   */
  submitPayment(request: TaxPaymentRequest): Observable<TaxPaymentResponse> {
    return this.http.post<TaxPaymentResponse>(
      `${this.apiUrl}/pay`,
      request,
      this.httpOptions
    );
  }

  /**
   * Retrieve all payments with optional filtering and pagination.
   * GET /api/v1/taxpayment
   */
  getPayments(params?: { npwp?: string; status?: string; taxType?: string; page?: number; pageSize?: number }): Observable<TaxPaymentResponse[]> {
    let httpParams = new HttpParams();
    if (params?.npwp) {
      httpParams = httpParams.set('npwp', params.npwp);
    }
    if (params?.status) {
      httpParams = httpParams.set('status', params.status);
    }
    if (params?.taxType) {
      httpParams = httpParams.set('taxType', params.taxType);
    }
    if (params?.page) {
      httpParams = httpParams.set('page', params.page.toString());
    }
    if (params?.pageSize) {
      httpParams = httpParams.set('pageSize', params.pageSize.toString());
    }

    return this.http.get<TaxPaymentResponse[]>(
      this.apiUrl,
      { ...this.httpOptions, params: httpParams }
    );
  }

  /**
   * Retrieve a specific payment by its ID.
   * GET /api/v1/taxpayment/{paymentId}
   */
  getPaymentById(paymentId: string): Observable<TaxPaymentResponse> {
    return this.http.get<TaxPaymentResponse>(
      `${this.apiUrl}/${paymentId}`,
      this.httpOptions
    );
  }

  /**
   * Verify a payment using the billing code.
   * GET /api/v1/taxpayment/verify/{billingCode}
   */
  verifyPayment(billingCode: string): Observable<TaxPaymentResponse> {
    return this.http.get<TaxPaymentResponse>(
      `${this.apiUrl}/verify/${billingCode}`,
      this.httpOptions
    );
  }

  /**
   * Download the payment receipt (Bukti Penerimaan Negara / NTPN).
   * GET /api/v1/taxpayment/receipt/{paymentId}
   */
  downloadPaymentReceipt(paymentId: string): Observable<Blob> {
    return this.http.get(
      `${this.apiUrl}/receipt/${paymentId}`,
      {
        responseType: 'blob',
        headers: new HttpHeaders({ 'Accept': 'application/pdf' })
      }
    );
  }
}
