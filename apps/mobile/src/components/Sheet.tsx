import { Ionicons } from "@expo/vector-icons";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useTheme } from "@/theme/context";
import { radius, space, tap, text } from "@/theme/tokens";

/**
 * Bottom sheet used for confirmations and short forms. Kept deliberately
 * simple: a modal with a scrim, a titled header, and a pinned footer so the
 * primary action never scrolls out of reach.
 */
export function Sheet({
  visible,
  onClose,
  title,
  subtitle,
  children,
  footer,
}: {
  visible: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  const theme = useTheme();
  const c = theme.color;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: "rgba(15, 27, 45, 0.45)" }}>
        <Pressable
          style={{ flex: 1 }}
          onPress={onClose}
          accessibilityRole="button"
          accessibilityLabel="Close sheet"
        />
        <SafeAreaView
          edges={["bottom"]}
          style={{
            backgroundColor: c.surface,
            borderTopLeftRadius: radius.xl,
            borderTopRightRadius: radius.xl,
            maxHeight: "88%",
          }}
        >
          <View
            style={{
              flexDirection: "row",
              alignItems: "flex-start",
              gap: space[3],
              padding: space[4],
              borderBottomWidth: 1,
              borderBottomColor: c.line,
            }}
          >
            <View style={{ flex: 1, gap: 2 }}>
              <Text
                accessibilityRole="header"
                style={{ fontSize: text.md, fontWeight: "800", color: c.ink }}
              >
                {title}
              </Text>
              {subtitle ? (
                <Text style={{ fontSize: text.sm, color: c.muted }}>{subtitle}</Text>
              ) : null}
            </View>
            <Pressable
              onPress={onClose}
              accessibilityRole="button"
              accessibilityLabel="Close"
              hitSlop={8}
              style={({ pressed }) => ({
                width: tap,
                height: tap,
                borderRadius: radius.pill,
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: pressed ? c.surface3 : "transparent",
              })}
            >
              <Ionicons name="close" size={22} color={c.muted} />
            </Pressable>
          </View>

          <ScrollView
            contentContainerStyle={{ padding: space[4], gap: space[4] }}
            keyboardShouldPersistTaps="handled"
          >
            {children}
          </ScrollView>

          {footer ? (
            <View
              style={{
                padding: space[4],
                borderTopWidth: 1,
                borderTopColor: c.line,
                gap: space[2],
              }}
            >
              {footer}
            </View>
          ) : null}
        </SafeAreaView>
      </View>
    </Modal>
  );
}
