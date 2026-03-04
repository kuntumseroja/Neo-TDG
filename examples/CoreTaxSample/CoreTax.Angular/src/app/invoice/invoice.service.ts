import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface InvoiceLineItem {
  itemName: string;
  quantity: number;
  unitPrice: number;
  discount: number;
  taxRate: number;
}

export interface InvoiceSubmitRequest {
  sellerNpwp: string;
  sellerName: string;
  buyerNpwp: string;
  buyerName: string;
  invoiceType: string;
  taxCode: string;
  transactionDate: string;
  description: string;
  lineItems: InvoiceLineItem[];
}

export interface InvoiceResponse {
  invoiceId: string;
  invoiceNumber: string;
  sellerNpwp: string;
  sellerName: string;
  buyerNpwp: string;
  buyerName: string;
  invoiceType: string;
  taxCode: string;
  transactionDate: string;
  subtotal: number;
  taxAmount: number;
  totalAmount: number;
  status: string;
  createdDate: string;
  lineItems: InvoiceLineItem[];
}

@Injectable({
  providedIn: 'root'
})
export class InvoiceService {
  private readonly apiUrl = `${environment.apiBaseUrl}/api/v1/invoices`;

  private httpOptions = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    })
  };

  constructor(private http: HttpClient) {}

  /**
   * Submit a new tax invoice (Faktur Pajak) to the CoreTax system.
   * POST /api/v1/invoices/submit
   */
  submitInvoice(request: InvoiceSubmitRequest): Observable<InvoiceResponse> {
    return this.http.post<InvoiceResponse>(
      `${this.apiUrl}/submit`,
      request,
      this.httpOptions
    );
  }

  /**
   * Retrieve all invoices with optional filtering and pagination.
   * GET /api/v1/invoices
   */
  getInvoices(params?: { npwp?: string; status?: string; page?: number; pageSize?: number }): Observable<InvoiceResponse[]> {
    let httpParams = new HttpParams();
    if (params?.npwp) {
      httpParams = httpParams.set('npwp', params.npwp);
    }
    if (params?.status) {
      httpParams = httpParams.set('status', params.status);
    }
    if (params?.page) {
      httpParams = httpParams.set('page', params.page.toString());
    }
    if (params?.pageSize) {
      httpParams = httpParams.set('pageSize', params.pageSize.toString());
    }

    return this.http.get<InvoiceResponse[]>(
      this.apiUrl,
      { ...this.httpOptions, params: httpParams }
    );
  }

  /**
   * Retrieve a specific invoice by its ID.
   * GET /api/v1/invoices/{invoiceId}
   */
  getInvoiceById(invoiceId: string): Observable<InvoiceResponse> {
    return this.http.get<InvoiceResponse>(
      `${this.apiUrl}/${invoiceId}`,
      this.httpOptions
    );
  }

  /**
   * Cancel an existing invoice.
   * PUT /api/v1/invoices/cancel/{invoiceId}
   */
  cancelInvoice(invoiceId: string): Observable<InvoiceResponse> {
    return this.http.put<InvoiceResponse>(
      `${this.apiUrl}/cancel/${invoiceId}`,
      {},
      this.httpOptions
    );
  }

  /**
   * Submit a replacement invoice for an existing invoice.
   * POST /api/v1/invoices/replace/{originalInvoiceId}
   */
  replaceInvoice(originalInvoiceId: string, request: InvoiceSubmitRequest): Observable<InvoiceResponse> {
    return this.http.post<InvoiceResponse>(
      `${this.apiUrl}/replace/${originalInvoiceId}`,
      request,
      this.httpOptions
    );
  }

  /**
   * Download the invoice PDF document.
   * GET /api/v1/invoices/download/{invoiceId}
   */
  downloadInvoicePdf(invoiceId: string): Observable<Blob> {
    return this.http.get(
      `${this.apiUrl}/download/${invoiceId}`,
      {
        responseType: 'blob',
        headers: new HttpHeaders({ 'Accept': 'application/pdf' })
      }
    );
  }
}
