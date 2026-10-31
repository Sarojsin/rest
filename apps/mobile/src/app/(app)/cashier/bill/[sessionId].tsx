import { Ionicons } from "@expo/vector-icons";
import { Image } from "expo-image";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { Pressable, Text, View } from "react-native";

import type { Bill, PaymentMethodConfig } from "@rest/api-client";
import { newIdempotencyKey } from "@rest/api-client";

import { Sheet } from "@/components/Sheet";
import {
  Badge,
  Banner,
  Button,
  Card,
  EmptyState,
  Field,
  KeyValue,
  Loading,
  Muted,
  Screen,
  SectionLabel,
  Subtitle,
  Title,
} from "@/components/ui";
import { useBill, useIssueBill, usePaymentMethods, useRecordPayment } from "@/features/bills/api";
import { useTables } from "@/features/tables/api";
import { ApiError, apiAuthHeaders, apiUrl } from "@/lib/api";
import { formatClock, formatMoney } from "@/lib/format";
import { useTheme } from "@/theme/context";
import { radius, space, text } from "@/theme/tokens";

/**
 * Checkout for one dining session.
 *
 * The bill is created and totalled by the server. This screen never computes a
 * price, tax, or settlement state — it only presents what the API returns and
 * asks the cashier to confirm the money arrived before recording a payment.
 */
export default function BillScreen() {
  const { sessionId } = useLocalSearchParams<{ sessionId: string }>();
  const theme = useTheme();
  const c = theme.color;

  const tables = useTables();
  const billQuery = useBill(sessionId);
  const methodsQuery = usePaymentMethods();
  const issueBill = useIssueBill();
  const recordPayment = useRecordPayment();

  const table = tables.data?.find((row) => row.active_session_id === sessionId);
  const bill = billQuery.data ?? null;

  const [sheetOpen, setSheetOpen] = useState(false);
  const [methodId, setMethodId] = useState<string | null>(null);
  const [amountText, setAmountText] = useState("");
  const [verified, setVerified] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [qrHeaders, setQrHeaders] = useState<Record<string, string>>({});

  const idempotencyKey = useRef(newIdempotencyKey());

  const methods = methodsQuery.data ?? [];
  const usableMethods = useMemo(
    () =>
      methods.filter(
        (method) => method.is_active && (method.kind === "CASH" || method.has_qr_image)
      ),
    [methods]
  );
  const blockedQrMethods = useMemo(
    () => methods.filter((method) => method.is_active && method.kind === "QR" && !method.has_qr_image),
    [methods]
  );

  const chosenMethod = usableMethods.find((method) => method.id === methodId) ?? null;
  const amountMinor = parseAmount(amountText);
  const resultingBalance = bill ? bill.balance_due_minor - amountMinor : 0;
  const payable = Boolean(bill && (bill.status === "ISSUED" || bill.status === "PARTIALLY_PAID"));

  useEffect(() => {
    void apiAuthHeaders().then(setQrHeaders);
  }, []);

  // A new amount or method is a new operation, so it needs a new key. Retrying
  // the same operation reuses the current one and cannot double-charge.
  useEffect(() => {
    idempotencyKey.current = newIdempotencyKey();
  }, [methodId, amountText]);

  function openPayment() {
    if (!bill) return;
    setError(null);
    setNotice(null);
    setVerified(false);
    setMethodId(usableMethods[0]?.id ?? null);
    setAmountText((bill.balance_due_minor / 100).toFixed(2));
    setSheetOpen(true);
  }

  function submitPayment() {
    if (!bill || !chosenMethod || !sessionId) return;
    if (amountMinor <= 0) {
      setError("Enter an amount greater than zero.");
      return;
    }
    if (amountMinor > bill.balance_due_minor) {
      setError("The amount cannot be more than the outstanding balance.");
      return;
    }
    setError(null);
    recordPayment.mutate(
      {
        billId: bill.id,
        sessionId,
        methodId: chosenMethod.id,
        amountMinor,
        note: "",
        idempotencyKey: idempotencyKey.current,
      },
      {
        onSuccess: (updated) => {
          setSheetOpen(false);
          setNotice(
            updated.status === "PAID"
              ? `Payment recorded via ${chosenMethod.label}. Bill settled and the session closed.`
              : `Payment recorded via ${chosenMethod.label}. ${formatMoney(
                  updated.balance_due_minor,
                  updated.currency_code
                )} still outstanding.`
          );
        },
        onError: (err) => {
          setError(
            err instanceof ApiError
              ? err.detail
              : "Could not confirm the payment. Check the bill before retrying — the charge may not have been recorded."
          );
        },
      }
    );
  }

  if (!sessionId) {
    return (
      <Screen>
        <EmptyState icon="alert-circle-outline" title="No session selected">
          Go back and pick an open table.
        </EmptyState>
      </Screen>
    );
  }

  return (
    <Screen
      refreshing={billQuery.isRefetching || tables.isRefetching}
      onRefresh={() => {
        void billQuery.refetch();
        void tables.refetch();
      }}
    >
      <View style={{ gap: space[4] }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: space[2] }}>
          <Pressable
            onPress={() => router.back()}
            accessibilityRole="button"
            accessibilityLabel="Back to checkout"
            hitSlop={8}
            style={({ pressed }) => ({
              width: 40,
              height: 40,
              borderRadius: radius.pill,
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: pressed ? c.surface3 : "transparent",
            })}
          >
            <Ionicons name="arrow-back" size={22} color={c.ink} />
          </Pressable>
          <View style={{ flex: 1, gap: 1 }}>
            <Title>{table?.display_name ?? "Table"}</Title>
            <Subtitle>
              {bill ? `Bill ${bill.id.slice(0, 8)} · ${bill.items.length} line${bill.items.length === 1 ? "" : "s"}` : "Checkout"}
            </Subtitle>
          </View>
          {bill ? <Badge status={bill.status} /> : null}
        </View>

        {notice ? <Banner tone="success">{notice}</Banner> : null}
        {error ? <Banner tone="danger">{error}</Banner> : null}

        {billQuery.isPending ? <Loading label="Loading bill" /> : null}

        {!billQuery.isPending && !bill ? (
          <Card>
            <SectionLabel>No bill yet</SectionLabel>
            <Subtitle>
              A bill is built from accepted items only. The server calculates tax and totals, so the
              figure is final once issued.
            </Subtitle>
            {issueBill.isPending ? (
              <Loading label="Issuing bill" />
            ) : (
              <Button
                label="Issue bill"
                icon="receipt"
                onPress={() => {
                  setError(null);
                  setNotice(null);
                  issueBill.mutate(sessionId, {
                    onSuccess: () => setNotice("Bill issued from accepted items."),
                    onError: (err) =>
                      setError(
                        err instanceof ApiError ? err.detail : "Could not issue the bill."
                      ),
                  });
                }}
              />
            )}
            <Muted>No open session? Seat the table by confirming a guest order first.</Muted>
          </Card>
        ) : null}

        {bill ? (
          <>
            <Card>
              <SectionLabel>Lines</SectionLabel>
              {bill.items.length === 0 ? (
                <Muted>This bill has no lines yet.</Muted>
              ) : (
                bill.items.map((item) => (
                  <View
                    key={item.id}
                    style={{ flexDirection: "row", gap: space[3], alignItems: "flex-start" }}
                  >
                    <Text
                      style={{
                        minWidth: 26,
                        fontSize: text.base,
                        fontWeight: "700",
                        color: c.primary,
                      }}
                    >
                      {item.quantity}×
                    </Text>
                    <View style={{ flex: 1, gap: 1 }}>
                      <Text style={{ fontSize: text.base, color: c.ink }}>
                        {item.description_snapshot}
                      </Text>
                      {item.tax_minor > 0 ? (
                        <Text style={{ fontSize: text.xs, color: c.muted }}>
                          tax {formatMoney(item.tax_minor, bill.currency_code)}
                        </Text>
                      ) : null}
                    </View>
                    <Text style={{ fontSize: text.sm, fontWeight: "600", color: c.ink }}>
                      {formatMoney(item.line_total_minor, bill.currency_code)}
                    </Text>
                  </View>
                ))
              )}

              <View style={{ height: 1, backgroundColor: c.line }} />

              <KeyValue
                label="Subtotal"
                value={formatMoney(bill.subtotal_minor, bill.currency_code)}
              />
              <KeyValue label="Tax" value={formatMoney(bill.tax_minor, bill.currency_code)} />
              {bill.paid_minor > 0 ? (
                <KeyValue
                  label="Already paid"
                  value={`−${formatMoney(bill.paid_minor, bill.currency_code)}`}
                />
              ) : null}
              <KeyValue
                label="Balance due"
                value={formatMoney(bill.balance_due_minor, bill.currency_code)}
                emphasis
              />
            </Card>

            {bill.status === "PAID" ? (
              <Banner tone="success" title="Settled">
                The session is closed and the table is free for the next guest.
              </Banner>
            ) : null}

            {bill.status === "VOID" ? (
              <Banner tone="warn" title="Bill voided">
                Issue a new bill if the table is still in service.
              </Banner>
            ) : null}

            {payable ? (
              <Card>
                <SectionLabel>Take payment</SectionLabel>
                <Subtitle>
                  Record money only after you have counted it or verified it in the payment app.
                </Subtitle>
                <Button
                  label={`Take payment · ${formatMoney(bill.balance_due_minor, bill.currency_code)}`}
                  icon="cash-outline"
                  onPress={openPayment}
                />
                {usableMethods.length === 0 ? (
                  <Banner tone="warn">
                    No usable payment methods. Ask the owner to add one under Payment methods.
                  </Banner>
                ) : null}
                {blockedQrMethods.length > 0 ? (
                  <Muted>
                    {blockedQrMethods.map((method) => method.label).join(", ")}{" "}
                    {blockedQrMethods.length === 1 ? "is" : "are"} hidden until a QR image is
                    uploaded under Payment methods.
                  </Muted>
                ) : null}
              </Card>
            ) : null}

            {bill.payments.length > 0 ? (
              <Card>
                <SectionLabel>Recorded payments</SectionLabel>
                {bill.payments.map((payment) => (
                  <View
                    key={payment.id}
                    style={{ flexDirection: "row", justifyContent: "space-between", gap: space[3] }}
                  >
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: text.base, color: c.ink }}>{payment.method}</Text>
                      <Text style={{ fontSize: text.xs, color: c.muted }}>
                        {payment.status} · {formatClock(payment.succeeded_at ?? payment.created_at)}
                      </Text>
                    </View>
                    <Text style={{ fontSize: text.base, fontWeight: "700", color: c.ink }}>
                      {formatMoney(payment.amount_minor, payment.currency_code)}
                    </Text>
                  </View>
                ))}
              </Card>
            ) : null}
          </>
        ) : null}
      </View>

      <Sheet
        visible={sheetOpen}
        onClose={() => setSheetOpen(false)}
        title="Record payment"
        subtitle={bill ? `${table?.display_name ?? "Table"} · balance ${formatMoney(bill.balance_due_minor, bill.currency_code)}` : undefined}
        footer={
          <>
            <Button
              label={
                recordPayment.isPending
                  ? "Recording…"
                  : chosenMethod?.kind === "CASH"
                    ? "Confirm cash received"
                    : "Confirm payment received"
              }
              variant="success"
              loading={recordPayment.isPending}
              disabled={!verified || amountMinor <= 0 || amountMinor > (bill?.balance_due_minor ?? 0)}
              onPress={submitPayment}
            />
            <Button
              label="Cancel"
              variant="ghost"
              onPress={() => setSheetOpen(false)}
              disabled={recordPayment.isPending}
            />
          </>
        }
      >
        {error ? <Banner tone="danger">{error}</Banner> : null}

        <Field
          label="Amount received"
          value={amountText}
          onChangeText={setAmountText}
          keyboardType="decimal-pad"
          hint={
            bill
              ? `Balance ${formatMoney(bill.balance_due_minor, bill.currency_code)} · after this payment ${formatMoney(
                  Math.max(0, resultingBalance),
                  bill.currency_code
                )} outstanding`
              : undefined
          }
        />

        <View style={{ gap: space[2] }}>
          <SectionLabel>Method</SectionLabel>
          {usableMethods.length === 0 ? (
            <Banner tone="warn">No usable payment methods configured.</Banner>
          ) : null}
          {usableMethods.map((method) => (
            <MethodChoice
              key={method.id}
              method={method}
              selected={method.id === methodId}
              onPress={() => {
                setMethodId(method.id);
                setVerified(false);
              }}
            />
          ))}
        </View>

        {chosenMethod?.kind === "QR" && chosenMethod.qr_image_url && bill ? (
          <View style={{ alignItems: "center", gap: space[2] }}>
            <Banner tone="warn" title="Show this code — not yet paid">
              The bill stays unpaid until you confirm the transfer below.
            </Banner>
            <Image
              source={{ uri: apiUrl(chosenMethod.qr_image_url), headers: qrHeaders }}
              style={{ width: 240, height: 240, backgroundColor: "#ffffff" }}
              contentFit="contain"
              accessibilityLabel={`${chosenMethod.label} payment QR code`}
            />
            {chosenMethod.account_hint ? <Muted>{chosenMethod.account_hint}</Muted> : null}
            {chosenMethod.instructions ? <Muted>{chosenMethod.instructions}</Muted> : null}
          </View>
        ) : null}

        <Pressable
          onPress={() => setVerified((value) => !value)}
          accessibilityRole="checkbox"
          accessibilityState={{ checked: verified }}
          accessibilityLabel={
            chosenMethod?.kind === "QR"
              ? `I have checked the ${chosenMethod.label} account and received the amount`
              : "I have counted the cash from this table"
          }
          style={{ flexDirection: "row", gap: space[3], alignItems: "flex-start" }}
        >
          <View
            style={{
              width: 24,
              height: 24,
              borderRadius: 6,
              borderWidth: 2,
              borderColor: verified ? c.success : c.lineStrong,
              backgroundColor: verified ? c.success : "transparent",
              alignItems: "center",
              justifyContent: "center",
              marginTop: 1,
            }}
          >
            {verified ? <Ionicons name="checkmark" size={16} color="#ffffff" /> : null}
          </View>
          <Text style={{ flex: 1, fontSize: text.base, color: c.ink }}>
            {chosenMethod?.kind === "QR"
              ? `I checked the ${chosenMethod.label} account and received ${formatMoney(
                  amountMinor,
                  bill?.currency_code ?? ""
                )}.`
              : `I counted ${formatMoney(amountMinor, bill?.currency_code ?? "")} in cash from this table.`}
          </Text>
        </Pressable>

        {verified ? (
          <Banner tone="warn" title="Verification pending">
            The bill is still unpaid until you press confirm.
          </Banner>
        ) : null}
      </Sheet>
    </Screen>
  );
}

function MethodChoice({
  method,
  selected,
  onPress,
}: {
  method: PaymentMethodConfig;
  selected: boolean;
  onPress: () => void;
}) {
  const theme = useTheme();
  const c = theme.color;
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      accessibilityLabel={`${method.label}${method.kind === "QR" ? ", QR transfer" : ", cash"}`}
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: space[3],
        borderWidth: 1,
        borderColor: selected ? c.primary : c.lineStrong,
        backgroundColor: selected ? c.primarySoft : c.surface,
        borderRadius: radius.md,
        padding: space[3],
        minHeight: 56,
      }}
    >
      <Ionicons
        name={method.kind === "QR" ? "qr-code-outline" : "cash-outline"}
        size={20}
        color={selected ? c.primary : c.muted}
      />
      <View style={{ flex: 1 }}>
        <Text style={{ fontSize: text.base, fontWeight: "700", color: c.ink }}>{method.label}</Text>
        {method.account_hint ? (
          <Text style={{ fontSize: text.xs, color: c.muted }}>{method.account_hint}</Text>
        ) : null}
      </View>
      {selected ? <Ionicons name="checkmark-circle" size={20} color={c.primary} /> : null}
    </Pressable>
  );
}

/** "12.50" → 1250. Returns 0 for anything that is not a positive amount. */
function parseAmount(value: string): number {
  const normalised = value.replace(/[^0-9.]/g, "");
  if (!normalised) return 0;
  const parsed = Number.parseFloat(normalised);
  if (!Number.isFinite(parsed) || parsed <= 0) return 0;
  return Math.round(parsed * 100);
}
