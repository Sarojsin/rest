import { http, HttpResponse } from 'msw';

const mockRestaurantId = 'restaurant-1';
const mockBranchId = 'branch-1';

export const handlers = [
  http.get('/api/v1/inventory/ingredients', () => {
    return HttpResponse.json([
      {
        id: 'ingredient-1',
        name: 'Tomatoes',
        code: 'TOM',
        sku: 'SKU-TOM-001',
        unit: 'kg',
        base_unit: 'kg',
        category: 'Vegetables',
        unit_conversions: { g: 1000 },
        current_stock: 50,
        minimum_stock: 10,
        cost_per_unit_minor: 200,
        storage_location: 'Walk-in Cooler A',
        branch_id: mockBranchId,
        status: 'IN_STOCK',
        supplier_id: 'supplier-1',
        supplier_name: 'Fresh Farms Co.',
      },
      {
        id: 'ingredient-2',
        name: 'Chicken Breast',
        code: 'CHK',
        sku: 'SKU-CHK-001',
        unit: 'kg',
        base_unit: 'kg',
        category: 'Meat',
        unit_conversions: { g: 1000 },
        current_stock: 5,
        minimum_stock: 8,
        cost_per_unit_minor: 800,
        storage_location: 'Freezer B',
        branch_id: mockBranchId,
        status: 'LOW_STOCK',
        supplier_id: 'supplier-2',
        supplier_name: 'Prime Meats Inc.',
      },
    ]);
  }),

  http.get('/api/v1/inventory/ingredients/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: 'Tomatoes',
      code: 'TOM',
      sku: 'SKU-TOM-001',
      unit: 'kg',
      base_unit: 'kg',
      category: 'Vegetables',
      unit_conversions: { g: 1000 },
      current_stock: 50,
      minimum_stock: 10,
      cost_per_unit_minor: 200,
      storage_location: 'Walk-in Cooler A',
      branch_id: mockBranchId,
      status: 'IN_STOCK',
      supplier_id: 'supplier-1',
      supplier_name: 'Fresh Farms Co.',
    });
  }),

  http.post('/api/v1/inventory/ingredients', async ({ request }) => {
    const body = (await request.json()) as Record<string, any>;
    return HttpResponse.json(
      {
        id: 'new-ingredient-1',
        ...body,
        status: 'IN_STOCK',
        supplier_name: 'Fresh Farms Co.',
      },
      { status: 201 }
    );
  }),

  http.patch('/api/v1/inventory/ingredients/:id', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, any>;
    return HttpResponse.json({
      id: params.id,
      name: 'Tomatoes',
      code: 'TOM',
      sku: 'SKU-TOM-001',
      unit: 'kg',
      base_unit: 'kg',
      category: 'Vegetables',
      unit_conversions: { g: 1000 },
      current_stock: 50,
      minimum_stock: 10,
      cost_per_unit_minor: 200,
      storage_location: 'Walk-in Cooler A',
      branch_id: mockBranchId,
      status: 'IN_STOCK',
      supplier_id: 'supplier-1',
      supplier_name: 'Fresh Farms Co.',
      ...body,
    });
  }),

  http.patch('/api/v1/inventory/ingredients/:id/stock', async ({ params, request }) => {
    const body = (await request.json()) as { new_stock: number; reason: string };
    return HttpResponse.json({
      id: params.id,
      name: 'Tomatoes',
      code: 'TOM',
      sku: 'SKU-TOM-001',
      unit: 'kg',
      base_unit: 'kg',
      category: 'Vegetables',
      unit_conversions: { g: 1000 },
      current_stock: body.new_stock,
      minimum_stock: 10,
      cost_per_unit_minor: 200,
      storage_location: 'Walk-in Cooler A',
      branch_id: mockBranchId,
      status: body.new_stock <= 10 ? 'LOW_STOCK' : 'IN_STOCK',
      supplier_id: 'supplier-1',
      supplier_name: 'Fresh Farms Co.',
    });
  }),

  http.get('/api/v1/inventory/suppliers', () => {
    return HttpResponse.json([
      {
        id: 'supplier-1',
        name: 'Fresh Farms Co.',
        contact_name: 'John Doe',
        phone: '+1-555-0101',
        email: 'john@freshfarms.com',
        address: '123 Farm Road',
        city: 'Springfield',
        state: 'IL',
        postal_code: '62701',
        country: 'USA',
        tax_id: '12-3456789',
        is_active: true,
        rating: 5,
        average_delivery_days: 2,
        notes: 'Reliable organic produce supplier',
      },
    ]);
  }),

  http.post('/api/v1/inventory/suppliers', async ({ request }) => {
    const body = (await request.json()) as Record<string, any>;
    return HttpResponse.json(
      {
        id: 'new-supplier-1',
        ...body,
      },
      { status: 201 }
    );
  }),

  http.get('/api/v1/inventory/purchase-orders', () => {
    return HttpResponse.json([
      {
        id: 'po-1',
        code: 'PO-2024-001',
        status: 'DRAFT',
        supplier_id: 'supplier-1',
        supplier_name: 'Fresh Farms Co.',
        expected_date: '2024-12-15T00:00:00Z',
        purchase_date: '2024-12-01T00:00:00Z',
        received_date: null,
        notes: 'Monthly produce order',
        total_minor: 50000,
        items: [
          {
            id: 'po-item-1',
            ingredient_id: 'ingredient-1',
            ingredient_name: 'Tomatoes',
            quantity: 100,
            unit_price_minor: 200,
            total_minor: 20000,
            received_quantity: 0,
          },
        ],
      },
    ]);
  }),

  http.post('/api/v1/inventory/purchase-orders', async ({ request }) => {
    const body = (await request.json()) as {
      code: string;
      supplier_id: string;
      expected_date: string;
      purchase_date: string;
      notes?: string;
      items: Array<{ ingredient_id: string; quantity: number; unit_price_minor: number }>;
    };
    return HttpResponse.json(
      {
        id: 'new-po-1',
        code: body.code,
        status: 'DRAFT',
        supplier_id: body.supplier_id,
        supplier_name: 'Fresh Farms Co.',
        expected_date: body.expected_date,
        purchase_date: body.purchase_date,
        received_date: null,
        notes: body.notes,
        total_minor: body.items.reduce((sum: number, item: { quantity: number; unit_price_minor: number }) => sum + item.quantity * item.unit_price_minor, 0),
        items: body.items.map((item: { ingredient_id: string; quantity: number; unit_price_minor: number }, index: number) => ({
          id: `new-po-item-${index}`,
          ingredient_id: item.ingredient_id,
          ingredient_name: 'Tomatoes',
          quantity: item.quantity,
          unit_price_minor: item.unit_price_minor,
          total_minor: item.quantity * item.unit_price_minor,
          received_quantity: 0,
        })),
      },
      { status: 201 }
    );
  }),

  http.post('/api/v1/inventory/purchase-orders/:id/receive', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      code: 'PO-2024-001',
      status: 'RECEIVED',
      supplier_id: 'supplier-1',
      supplier_name: 'Fresh Farms Co.',
      expected_date: '2024-12-15T00:00:00Z',
      purchase_date: '2024-12-01T00:00:00Z',
      received_date: new Date().toISOString(),
      notes: 'Monthly produce order',
      total_minor: 50000,
      items: [
        {
          id: 'po-item-1',
          ingredient_id: 'ingredient-1',
          ingredient_name: 'Tomatoes',
          quantity: 100,
          unit_price_minor: 200,
          total_minor: 20000,
          received_quantity: 100,
        },
      ],
    });
  }),

  http.get('/api/v1/inventory/stock-movements', () => {
    return HttpResponse.json([
      {
        id: 'movement-1',
        ingredient_id: 'ingredient-1',
        movement_type: 'RECEIVE',
        quantity: 50,
        previous_balance: 0,
        new_balance: 50,
        reason: 'Received from PO-2024-001',
        reference_type: 'PO',
        reference_id: 'po-1',
        batch_id: 'batch-1',
        branch_id: mockBranchId,
        idempotency_key: 'idem-1',
        recorded_by: 'user-1',
        created_at: new Date().toISOString(),
      },
    ]);
  }),

  http.post('/api/v1/inventory/stock-movements', async ({ request }) => {
    const body = (await request.json()) as Record<string, any>;
    return HttpResponse.json(
      {
        id: 'new-movement-1',
        ...body,
        previous_balance: 50,
        new_balance: body.movement_type === 'RECEIVE' ? 100 : 30,
        recorded_by: 'user-1',
        created_at: new Date().toISOString(),
      },
      { status: 201 }
    );
  }),

  http.get('/api/v1/inventory/batches', () => {
    return HttpResponse.json([
      {
        id: 'batch-1',
        ingredient_id: 'ingredient-1',
        ingredient_name: 'Tomatoes',
        batch_no: 'BATCH-001',
        expiry_date: '2024-12-31T00:00:00Z',
        quantity: 50,
        cost_per_unit_minor: 200,
        is_expired: false,
        created_at: '2024-12-01T00:00:00Z',
      },
    ]);
  }),

  http.post('/api/v1/inventory/batches', async ({ request }) => {
    const body = (await request.json()) as Record<string, any>;
    return HttpResponse.json(
      {
        id: 'new-batch-1',
        ...body,
        ingredient_name: 'Tomatoes',
        is_expired: false,
        created_at: new Date().toISOString(),
      },
      { status: 201 }
    );
  }),

  http.get('/api/v1/inventory/stock-counts', () => {
    return HttpResponse.json([
      {
        id: 'count-1',
        branch_id: mockBranchId,
        count_date: '2024-12-01T00:00:00Z',
        status: 'COMPLETED',
        notes: 'Monthly inventory count',
        items: [
          {
            id: 'count-item-1',
            ingredient_id: 'ingredient-1',
            ingredient_name: 'Tomatoes',
            expected_qty: 50,
            counted_qty: 48,
            variance_qty: -2,
          },
        ],
        created_at: '2024-12-01T00:00:00Z',
      },
    ]);
  }),

  http.post('/api/v1/inventory/stock-counts', async ({ request }) => {
    const body = (await request.json()) as {
      branch_id?: string;
      count_date?: string;
      notes?: string;
      items: Array<{ ingredient_id: string; expected_qty: number; counted_qty: number }>;
    };
    return HttpResponse.json(
      {
        id: 'new-count-1',
        branch_id: body.branch_id || mockBranchId,
        count_date: body.count_date || new Date().toISOString(),
        status: 'DRAFT',
        notes: body.notes,
        items: body.items.map((item: { ingredient_id: string; expected_qty: number; counted_qty: number }, index: number) => ({
          id: `new-count-item-${index}`,
          ingredient_id: item.ingredient_id,
          ingredient_name: 'Tomatoes',
          expected_qty: item.expected_qty,
          counted_qty: item.counted_qty,
          variance_qty: item.counted_qty - item.expected_qty,
        })),
        created_at: new Date().toISOString(),
      },
      { status: 201 }
    );
  }),

  http.post('/api/v1/inventory/stock-counts/:id/complete', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      branch_id: mockBranchId,
      count_date: '2024-12-01T00:00:00Z',
      status: 'COMPLETED',
      notes: 'Monthly inventory count',
      items: [
        {
          id: 'count-item-1',
          ingredient_id: 'ingredient-1',
          ingredient_name: 'Tomatoes',
          expected_qty: 50,
          counted_qty: 48,
          variance_qty: -2,
        },
      ],
      created_at: '2024-12-01T00:00:00Z',
    });
  }),

  http.get('/api/v1/inventory/recipes', () => {
    return HttpResponse.json([
      {
        id: 'recipe-1',
        ingredient_id: 'ingredient-1',
        menu_item_id: 'menu-item-1',
        ingredient_name: 'Tomatoes',
        quantity_per_serving: 100,
        quantity_per_order: 100,
        ingredient_unit: 'g',
      },
    ]);
  }),

  http.put('/api/v1/inventory/recipes/:menuItemId', async ({ request }) => {
    const body = (await request.json()) as {
      items: Array<{ ingredient_id: string; quantity_per_serving: number; quantity_per_order?: number }>;
    };
    return HttpResponse.json(
      body.items.map((item: { ingredient_id: string; quantity_per_serving: number; quantity_per_order?: number }, index: number) => ({
        id: `recipe-${index}`,
        ingredient_id: item.ingredient_id,
        menu_item_id: 'menu-item-1',
        ingredient_name: 'Tomatoes',
        quantity_per_serving: item.quantity_per_serving,
        quantity_per_order: item.quantity_per_order || item.quantity_per_serving,
        ingredient_unit: 'g',
      }))
    );
  }),

  http.get('/api/v1/inventory/recipes/:menuItemId/cost', () => {
    return HttpResponse.json([
      {
        ingredient_id: 'ingredient-1',
        ingredient_name: 'Tomatoes',
        quantity: 100,
        unit_cost_minor: 200,
        total_cost_minor: 20,
      },
    ]);
  }),

  http.get('/api/v1/inventory/reports/low-stock', () => {
    return HttpResponse.json({
      restaurant_id: mockRestaurantId,
      low_stock_count: 1,
      ingredients: [
        {
          id: 'ingredient-2',
          name: 'Chicken Breast',
          sku: 'SKU-CHK-001',
          current_stock: 5,
          minimum_stock: 8,
          unit: 'kg',
          storage_location: 'Freezer B',
        },
      ],
    });
  }),

  http.get('/api/v1/inventory/reports/consumption', () => {
    return HttpResponse.json({
      restaurant_id: mockRestaurantId,
      consumption: [
        {
          ingredient_id: 'ingredient-1',
          ingredient_name: 'Tomatoes',
          total_deducted: 150,
          unit: 'kg',
        },
        {
          ingredient_id: 'ingredient-2',
          ingredient_name: 'Chicken Breast',
          total_deducted: 80,
          unit: 'kg',
        },
      ],
    });
  }),

  http.get('/api/v1/inventory/reports/waste', () => {
    return HttpResponse.json({
      restaurant_id: mockRestaurantId,
      window_days: 30,
      event_count: 5,
      waste: [
        {
          ingredient_id: 'ingredient-1',
          ingredient_name: 'Tomatoes',
          total_wasted: 5,
          event_count: 2,
          unit: 'kg',
        },
      ],
    });
  }),

  http.get('/api/v1/inventory/reports/expiring-batches', () => {
    return HttpResponse.json({
      restaurant_id: mockRestaurantId,
      window_days: 7,
      batches: [
        {
          id: 'batch-1',
          batch_no: 'BATCH-001',
          ingredient_id: 'ingredient-1',
          ingredient_name: 'Tomatoes',
          unit: 'kg',
          expiry_date: '2024-12-15T00:00:00Z',
          quantity: 10,
          cost_value_minor: 2000,
          expired: false,
        },
      ],
    })
  }),

  http.get('/api/v1/reports/sales', () => {
    return HttpResponse.json({
      currency_code: 'USD',
      order_count: 150,
      accepted_order_count: 145,
      cancelled_order_count: 5,
      gross_sales_minor: 1250000,
      tax_minor: 125000,
      collected_minor: 1300000,
      outstanding_minor: 75000,
      top_items: [
        { name: 'Margherita Pizza', quantity: 45, sales_minor: 450000 },
        { name: 'Chicken Burger', quantity: 38, sales_minor: 380000 },
      ],
    });
  }),

  http.get('/api/v1/reports/advanced', () => {
    return HttpResponse.json({
      window_days: 30,
      currency_code: 'USD',
      sales: {
        currency_code: 'USD',
        order_count: 150,
        accepted_order_count: 145,
        cancelled_order_count: 5,
        gross_sales_minor: 1250000,
        tax_minor: 125000,
        collected_minor: 1300000,
        outstanding_minor: 75000,
        top_items: [
          { name: 'Margherita Pizza', quantity: 45, sales_minor: 450000 },
        ],
      },
      average_order_minor: 8620,
      daily: [
        { date: '2024-11-01', order_count: 5, gross_sales_minor: 42000 },
        { date: '2024-11-02', order_count: 7, gross_sales_minor: 58000 },
      ],
    });
  }),

  http.get('/api/v1/reports/payments', () => {
    return HttpResponse.json({
      window_days: 30,
      currency_code: 'USD',
      total_collected_minor: 1300000,
      succeeded_count: 142,
      failed_count: 3,
      methods: [
        { method: 'Cash', payment_count: 60, amount_minor: 550000 },
        { method: 'Card', payment_count: 82, amount_minor: 750000 },
      ],
    });
  }),

  http.get('/api/v1/reports/kitchen-speed', () => {
    return HttpResponse.json({
      window_days: 30,
      completed_ticket_count: 200,
      avg_prep_seconds: 420,
      fastest_prep_seconds: 180,
      slowest_prep_seconds: 900,
      slowest_tickets: [
        {
          ticket_id: 'ticket-1',
          ticket_number: 15,
          status: 'READY',
          started_at: '2024-11-01T12:00:00Z',
          ready_at: '2024-11-01T12:15:00Z',
          prep_seconds: 900,
        },
      ],
    });
  }),

  http.get('/api/v1/audit-events', () => {
    return HttpResponse.json([
      {
        id: 'audit-1',
        action: 'CREATE',
        entity_type: 'Ingredient',
        entity_id: 'ingredient-1',
        occurred_at: new Date().toISOString(),
        detail: 'Created ingredient: Tomatoes',
      },
    ]);
  }),

  http.get('/api/v1/employees', () => {
    return HttpResponse.json([
      {
        id: 'employee-1',
        name: 'John Smith',
        email: 'john@restaurant.com',
        phone: '+1-555-0101',
        role: 'WAITER',
        hire_date: '2024-01-15T00:00:00Z',
        is_active: true,
        branch_id: mockBranchId,
        user_id: 'user-2',
        created_at: '2024-01-15T00:00:00Z',
        updated_at: '2024-01-15T00:00:00Z',
      },
      {
        id: 'employee-2',
        name: 'Jane Doe',
        email: 'jane@restaurant.com',
        phone: '+1-555-0102',
        role: 'KITCHEN',
        hire_date: '2024-02-01T00:00:00Z',
        is_active: true,
        branch_id: mockBranchId,
        user_id: 'user-3',
        created_at: '2024-02-01T00:00:00Z',
        updated_at: '2024-02-01T00:00:00Z',
      },
    ]);
  }),

  http.post('/api/v1/employees', async ({ request }) => {
    const body = (await request.json()) as Record<string, any>;
    return HttpResponse.json(
      {
        id: 'new-employee-1',
        ...body,
        user_id: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      { status: 201 }
    );
  }),

  http.patch('/api/v1/employees/:id', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, any>;
    return HttpResponse.json({
      id: params.id,
      name: 'John Smith',
      email: 'john@restaurant.com',
      phone: '+1-555-0101',
      role: 'WAITER',
      hire_date: '2024-01-15T00:00:00Z',
      is_active: true,
      branch_id: mockBranchId,
      user_id: 'user-2',
      created_at: '2024-01-15T00:00:00Z',
      updated_at: new Date().toISOString(),
      ...body,
    });
  }),

  http.get('/api/v1/employees/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: 'John Smith',
      email: 'john@restaurant.com',
      phone: '+1-555-0101',
      role: 'WAITER',
      hire_date: '2024-01-15T00:00:00Z',
      is_active: true,
      branch_id: mockBranchId,
      user_id: 'user-2',
      created_at: '2024-01-15T00:00:00Z',
      updated_at: '2024-01-15T00:00:00Z',
    });
  }),

  http.get('/api/v1/shifts', () => {
    return HttpResponse.json([
      {
        id: 'shift-1',
        employee_id: 'employee-1',
        branch_id: mockBranchId,
        date: '2024-12-01',
        start_time: '09:00',
        end_time: '17:00',
        status: 'SCHEDULED',
        notes: 'Morning shift',
        created_at: '2024-11-25T00:00:00Z',
      },
    ]);
  }),

  http.post('/api/v1/shifts', async ({ request }) => {
    const body = (await request.json()) as Record<string, any>;
    return HttpResponse.json(
      {
        id: 'new-shift-1',
        ...body,
        created_at: new Date().toISOString(),
      },
      { status: 201 }
    );
  }),

  http.post('/api/v1/shifts/:id/assign', async ({ params, request }) => {
    const body = (await request.json()) as { employee_id: string; membership_id: string };
    return HttpResponse.json(
      {
        id: 'new-assignment-1',
        shift_id: params.id,
        employee_id: body.employee_id,
        assigned_by_membership_id: body.membership_id,
        accepted_by_employee: false,
        accepted_at: null,
      },
      { status: 201 }
    );
  }),

  http.get('/api/v1/orders', () => {
    return HttpResponse.json([
      {
        id: 'order-1',
        table_id: 'table-1',
        dining_session_id: 'session-1',
        source: 'QR',
        status: 'PENDING',
        customer_note: 'No onions please',
        submitted_at: new Date().toISOString(),
        accepted_at: null,
        rejected_at: null,
        rejection_reason_code: null,
        rejection_note: '',
        version: 1,
        claim_state: 'UNCLAIMED',
        claimed_by_membership_id: null,
        claimed_at: null,
        claim_timeout_at: null,
        escalated_by_membership_id: null,
        escalated_at: null,
        items: [
          {
            id: 'order-item-1',
            menu_item_id: 'menu-item-1',
            item_name_snapshot: 'Margherita Pizza',
            quantity: 1,
            unit_price_minor: 1500,
            tax_minor: 150,
            line_total_minor: 1650,
            currency_code: 'USD',
            special_instructions: 'No onions',
          },
        ],
        subtotal_minor: 1500,
        tax_minor: 150,
        total_minor: 1650,
        currency_code: 'USD',
      },
    ]);
  }),

  http.post('/api/v1/orders/:id/claim', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      table_id: 'table-1',
      dining_session_id: 'session-1',
      source: 'QR',
      status: 'ACCEPTED',
      customer_note: 'No onions please',
      submitted_at: new Date().toISOString(),
      accepted_at: new Date().toISOString(),
      rejected_at: null,
      rejection_reason_code: null,
      rejection_note: '',
      version: 2,
      claim_state: 'CLAIMED',
      claimed_by_membership_id: 'membership-1',
      claimed_at: new Date().toISOString(),
      claim_timeout_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
      escalated_by_membership_id: null,
      escalated_at: null,
      items: [
        {
          id: 'order-item-1',
          menu_item_id: 'menu-item-1',
          item_name_snapshot: 'Margherita Pizza',
          quantity: 1,
          unit_price_minor: 1500,
          tax_minor: 150,
          line_total_minor: 1650,
          currency_code: 'USD',
          special_instructions: 'No onions',
        },
      ],
      subtotal_minor: 1500,
      tax_minor: 150,
      total_minor: 1650,
      currency_code: 'USD',
    });
  }),

  http.post('/api/v1/orders/:id/escalate', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      table_id: 'table-1',
      dining_session_id: 'session-1',
      source: 'QR',
      status: 'ACCEPTED',
      customer_note: 'No onions please',
      submitted_at: new Date().toISOString(),
      accepted_at: new Date().toISOString(),
      rejected_at: null,
      rejection_reason_code: null,
      rejection_note: '',
      version: 2,
      claim_state: 'ESCALATED',
      claimed_by_membership_id: 'membership-1',
      claimed_at: new Date().toISOString(),
      claim_timeout_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
      escalated_by_membership_id: 'membership-1',
      escalated_at: new Date().toISOString(),
      items: [
        {
          id: 'order-item-1',
          menu_item_id: 'menu-item-1',
          item_name_snapshot: 'Margherita Pizza',
          quantity: 1,
          unit_price_minor: 1500,
          tax_minor: 150,
          line_total_minor: 1650,
          currency_code: 'USD',
          special_instructions: 'No onions',
        },
      ],
      subtotal_minor: 1500,
      tax_minor: 150,
      total_minor: 1650,
      currency_code: 'USD',
    });
  }),
];