using MassTransit;
using CoreTax.Contracts.Events;

namespace CoreTax.Worker.Sagas;

public class InvoiceApprovalState : SagaStateMachineInstance
{
    public Guid CorrelationId { get; set; }
    public string CurrentState { get; set; } = string.Empty;
    public Guid InvoiceId { get; set; }
    public string InvoiceNumber { get; set; } = string.Empty;
    public string SellerNpwp { get; set; } = string.Empty;
    public decimal TaxableAmount { get; set; }
    public DateTime SubmittedAt { get; set; }
    public DateTime? ApprovedAt { get; set; }
    public int RetryCount { get; set; }
}

public class InvoiceApprovalSaga : MassTransitStateMachine<InvoiceApprovalState>
{
    public State Submitted { get; private set; }
    public State Validating { get; private set; }
    public State Approved { get; private set; }
    public State Rejected { get; private set; }

    public Event<InvoiceSubmittedEvent> InvoiceSubmitted { get; private set; }

    public InvoiceApprovalSaga()
    {
        InstanceState(x => x.CurrentState);

        Event(() => InvoiceSubmitted, x =>
            x.CorrelateById(context => context.Message.InvoiceId));

        Initially(
            When(InvoiceSubmitted)
                .Then(context =>
                {
                    context.Saga.InvoiceId = context.Message.InvoiceId;
                    context.Saga.InvoiceNumber = context.Message.InvoiceNumber;
                    context.Saga.SellerNpwp = context.Message.SellerNpwp;
                    context.Saga.TaxableAmount = context.Message.TaxableAmount;
                    context.Saga.SubmittedAt = context.Message.SubmittedAt;
                })
                .TransitionTo(Validating)
        );
    }
}
