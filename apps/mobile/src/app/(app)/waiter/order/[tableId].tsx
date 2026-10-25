import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useMemo, useRef, useState } from "react";
import { Pressable, Text, View } from "react-native";

import type { MenuItem } from "@rest/api-client";
import { newIdempotencyKey } from "@rest/api-client";

import { Sheet } from "@/components/Sheet";
import {
  Badge,
  Banner,
  Button,
  Card,
  EmptyState,
  Field,
  Loading,
  Muted,
  Screen,
  Stepper,
  Subtitle,
  Title,
} from "@/components/ui";
import { useCreateOrder, useMenu, useOrders } from "@/features/orders/api";
import { useTable } from "@/features/tables/api";
import { ApiError } from "@/lib/api";
import { elapsed, formatMoney } from "@/lib/format";
import { useNow } from "@/lib/useNow";
import { useTheme } from "@/theme/context";
import { radius, space, text } from "@/theme/tokens";

type Draft = Record<string, { item: MenuItem; quantity: number }>;

/**
 * Take an order at the table. Prices are the server's catalog values; the
 * subtotal here is a preview and the server recomputes tax and totals when the
 * order is created.
 */
export default function TakeOrderScreen() {
  const { tableId } = useLocalSearchParams<{ tableId: string }>();
  const theme = useTheme();
  const c = theme.color;
  const now = useNow(30_000);

  const table = useTable(tableId);
  const menu = useMenu();
  const accepted = useOrders("ACCEPTED", { refetchInterval: 15_000 });
  const createOrder = useCreateOrder();

  const [draft, setDraft] = useState<Draft>({});
  const [note, setNote] = useState("");
  const [reviewOpen, setReviewOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // One key per draft: a retry after a timeout must not create a second order.
  const idempotencyKey = useRef(newIdempotencyKey());

  const lines = useMemo(
    () => Object.values(draft).filter((line) => line.quantity > 0),
    [draft]
  );
  const itemCount = lines.reduce((total, line) => total + line.quantity, 0);
  const subtotal = lines.reduce(
    (total, line) => total + line.item.current_price_minor * line.quantity,
    0
  );
  const currency =
    lines[0]?.item.currency_code ??
    menu.data?.flatMap((category) => category.items)[0]?.currency_code ??
    "USD";

  const tableOrders = (accepted.data ?? []).filter((order) => order.table_id === tableId);

  function setQuantity(item: MenuItem, quantity: number) {
    setDraft((previous) => {
      const next = { ...previous };
      if (quantity <= 0) delete next[item.id];
      else next[item.id] = { item, quantity };
      return next;
    });
  }

  function submit() {
    if (!tableId || lines.length === 0) return;
    setError(null);
    setNotice(null);
    createOrder.mutate(
      {
        tableId,
        items: lines.map((line) => ({
          menuItemId: line.item.id,
          quantity: line.quantity,
          specialInstructions: "",
        })),
        customerNote: note.trim(),
        idempotencyKey: idempotencyKey.current,
      },
      {
        onSuccess: (order) => {
          setDraft({});
          setNote("");
          setReviewOpen(false);
          // A fresh draft needs a fresh key; reusing it would replay the old order.
          idempotencyKey.current = newIdempotencyKey();
          setNotice(
            `Order ${order.id.slice(0, 8)} accepted and sent to the kitchen. It is already on the ticket board.`
          );
        },
        onError: (err) => {
          setError(
            err instanceof ApiError
              ? err.detail
              : "Could not confirm the order. Your items are still here — retry when the connection is back."
          );
        },
      }
    );
  }

  if (!tableId) {
    return (
      <Screen>
        <EmptyState icon="alert-circle-outline" title="No table selected">
          Go back to the floor and pick a table.
        </EmptyState>
      </Screen>
    );
  }

  const categories = (menu.data ?? []).filter((category) =>
    category.items.some((item) => item.status === "PUBLISHED")
  );

  return (
    <Screen
      scroll
      footer={
        <View
          style={{
            borderTopWidth: 1,
            borderTopColor: c.line,
            backgroundColor: c.surface,
            padding: space[4],
            gap: space[2],
          }}
        >
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            <Text style={{ fontSize: text.sm, color: c.muted }}>
              {itemCount === 0
                ? "Nothing selected"
                : `${itemCount} item${itemCount === 1 ? "" : "s"}`}
            </Text>
            <Text style={{ fontSize: text.md, fontWeight: "800", color: c.ink }}>
              {formatMoney(subtotal, currency)}
            </Text>
          </View>
          <Button
            label={itemCount === 0 ? "Add items to continue" : "Review order"}
            disabled={itemCount === 0}
            onPress={() => setReviewOpen(true)}
          />
        </View>
      }
    >
      <View style={{ gap: space[4] }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: space[2] }}>
          <Pressable
            onPress={() => router.back()}
            accessibilityRole="button"
            accessibilityLabel="Back to tables"
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
              {table?.seating_capacity ? `${table.seating_capacity} seats · ` : ""}
              New order
            </Subtitle>
          </View>
          {table ? <Badge status={table.occupancy} /> : null}
        </View>

        {notice ? <Banner tone="success">{notice}</Banner> : null}
        {error ? <Banner tone="danger">{error}</Banner> : null}

        {tableOrders.length > 0 ? (
          <View style={{ gap: space[2] }}>
            <Text style={{ fontSize: text.xs, fontWeight: "700", color: c.muted }}>
              ALREADY ON THIS TABLE
            </Text>
            {tableOrders.map((order) => (
              <Card key={order.id} style={{ paddingVertical: space[3] }}>
                <View
                  style={{ flexDirection: "row", justifyContent: "space-between", gap: space[3] }}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: text.base, fontWeight: "700", color: c.ink }}>
                      {order.items.reduce((total, item) => total + item.quantity, 0)} items ·{" "}
                      {elapsed(order.accepted_at ?? order.submitted_at, now)} ago
                    </Text>
                    <Muted>{order.items.map((item) => item.item_name_snapshot).join(", ")}</Muted>
                  </View>
                  <Badge status={order.status} />
                </View>
              </Card>
            ))}
          </View>
        ) : null}

        {menu.isPending ? <Loading label="Loading the menu" /> : null}
        {menu.isError ? (
          <Banner tone="danger" title="Could not load the menu">
            {menu.error instanceof Error ? menu.error.message : "Check the connection."}
          </Banner>
        ) : null}

        {!menu.isPending && categories.length === 0 && !menu.isError ? (
          <EmptyState icon="book-outline" title="No published menu items">
            An owner or manager publishes items under Menu in the staff website.
          </EmptyState>
        ) : null}

        {categories.map((category) => (
          <View key={category.id} style={{ gap: space[2] }}>
            <View
              style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" }}
            >
              <Text style={{ fontSize: text.md, fontWeight: "800", color: c.ink }}>
                {category.name}
              </Text>
              <Text style={{ fontSize: text.xs, color: c.muted }}>
                {category.items.filter((item) => item.status === "PUBLISHED").length} available
              </Text>
            </View>

            {category.items
              .filter((item) => item.status === "PUBLISHED")
              .map((item) => {
                const quantity = draft[item.id]?.quantity ?? 0;
                return (
                  <Card key={item.id} style={{ paddingVertical: space[3] }}>
                    <View style={{ flexDirection: "row", gap: space[3], alignItems: "center" }}>
                      <View style={{ flex: 1, gap: 2 }}>
                        <Text style={{ fontSize: text.base, fontWeight: "700", color: c.ink }}>
                          {item.image_emoji ? `${item.image_emoji} ` : ""}
                          {item.name}
                        </Text>
                        <Text style={{ fontSize: text.xs, color: c.muted }} numberOfLines={2}>
                          {item.description || "No description"}
                        </Text>
                        <Text style={{ fontSize: text.sm, fontWeight: "700", color: c.ink }}>
                          {formatMoney(item.current_price_minor, item.currency_code)}
                        </Text>
                      </View>
                      <Stepper
                        value={quantity}
                        onChange={(next) => setQuantity(item, next)}
                        label={item.name}
                      />
                    </View>
                  </Card>
                );
              })}
          </View>
        ))}
      </View>

      <Sheet
        visible={reviewOpen}
        onClose={() => setReviewOpen(false)}
        title="Review order"
        subtitle={`${table?.display_name ?? "Table"} · the kitchen sees this immediately after you send it.`}
        footer={
          <>
            <Button
              label={createOrder.isPending ? "Sending…" : "Send to kitchen"}
              loading={createOrder.isPending}
              onPress={submit}
              disabled={lines.length === 0}
              accessibilityHint="Creates the order and adds it to the kitchen board"
            />
            <Button
              label="Keep editing"
              variant="ghost"
              onPress={() => setReviewOpen(false)}
              disabled={createOrder.isPending}
            />
          </>
        }
      >
        {error ? <Banner tone="danger">{error}</Banner> : null}

        <View style={{ gap: space[2] }}>
          {lines.map((line) => (
            <View
              key={line.item.id}
              style={{ flexDirection: "row", justifyContent: "space-between", gap: space[3] }}
            >
              <Text style={{ flex: 1, fontSize: text.base, color: c.ink }}>
                {line.quantity} × {line.item.name}
              </Text>
              <Text style={{ fontSize: text.base, fontWeight: "700", color: c.ink }}>
                {formatMoney(
                  line.item.current_price_minor * line.quantity,
                  line.item.currency_code
                )}
              </Text>
            </View>
          ))}
        </View>

        <Field
          label="Ticket note"
          value={note}
          onChangeText={setNote}
          placeholder="e.g. One plate to share, no chilli"
          maxLength={280}
          hint={`${note.length}/280`}
        />

        <View
          style={{
            flexDirection: "row",
            justifyContent: "space-between",
            borderTopWidth: 1,
            borderTopColor: c.line,
            paddingTop: space[3],
          }}
        >
          <Text style={{ fontSize: text.md, color: c.muted }}>Subtotal</Text>
          <Text style={{ fontSize: text.md, fontWeight: "800", color: c.ink }}>
            {formatMoney(subtotal, currency)}
          </Text>
        </View>
        <Text style={{ fontSize: text.xs, color: c.muted }}>
          Tax and the final total are calculated by the server when the order is accepted.
        </Text>
      </Sheet>
    </Screen>
  );
}
