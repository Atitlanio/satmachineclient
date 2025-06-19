window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  delimiters: ['${', '}'],
  data: function () {
    return {
      // DCA Admin Data
      dcaClients: [],
      deposits: [],

      // Table configurations
      clientsTable: {
        columns: [
          { name: 'username', align: 'left', label: 'Username', field: 'username' },
          { name: 'user_id', align: 'left', label: 'User ID', field: 'user_id' },
          { name: 'wallet_id', align: 'left', label: 'Wallet ID', field: 'wallet_id' },
          { name: 'dca_mode', align: 'left', label: 'DCA Mode', field: 'dca_mode' },
          { name: 'fixed_mode_daily_limit', align: 'left', label: 'Daily Limit', field: 'fixed_mode_daily_limit' },
          { name: 'status', align: 'left', label: 'Status', field: 'status' }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      depositsTable: {
        columns: [
          { name: 'client_id', align: 'left', label: 'Client', field: 'client_id' },
          { name: 'amount', align: 'left', label: 'Amount', field: 'amount' },
          { name: 'currency', align: 'left', label: 'Currency', field: 'currency' },
          { name: 'status', align: 'left', label: 'Status', field: 'status' },
          { name: 'created_at', align: 'left', label: 'Created', field: 'created_at' },
          { name: 'notes', align: 'left', label: 'Notes', field: 'notes' }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },

      // Dialog states  
      depositFormDialog: {
        show: false,
        data: {
          currency: 'GTQ'
        }
      },
      clientDetailsDialog: {
        show: false,
        data: null,
        balance: null
      },

      // Quick deposit form
      quickDepositForm: {
        selectedClient: null,
        amount: null,
        notes: ''
      },
      
      // Polling status
      lastPollTime: null,
      testingConnection: false,
      runningManualPoll: false,
      lamassuConfig: null,
      
      // Config dialog
      configDialog: {
        show: false,
        data: {
          host: '',
          port: 5432,
          database_name: '',
          username: '',
          password: '',
          selectedWallet: null,
          selectedCommissionWallet: null,
          // SSH Tunnel settings
          use_ssh_tunnel: false,
          ssh_host: '',
          ssh_port: 22,
          ssh_username: '',
          ssh_password: '',
          ssh_private_key: ''
        }
      },

      // Options
      currencyOptions: [
        { label: 'GTQ', value: 'GTQ' },
        { label: 'USD', value: 'USD' }
      ],

      // Legacy data (keep for backward compatibility)
      invoiceAmount: 10,
      qrValue: 'lnurlpay',
      myex: [],
      myexTable: {
        columns: [
          { name: 'id', align: 'left', label: 'ID', field: 'id' },
          { name: 'name', align: 'left', label: 'Name', field: 'name' },
          { name: 'wallet', align: 'left', label: 'Wallet', field: 'wallet' },
          { name: 'total', align: 'left', label: 'Total sent/received', field: 'total' }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      formDialog: {
        show: false,
        data: {},
        advanced: {}
      },
      urlDialog: {
        show: false,
        data: {}
      }
    }
  },

  ///////////////////////////////////////////////////
  ////////////////METHODS FUNCTIONS//////////////////
  ///////////////////////////////////////////////////

  methods: {
    // Utility Methods
    formatCurrency(amount) {
      if (!amount) return 'Q 0.00';

      return new Intl.NumberFormat('es-GT', {
        style: 'currency',
        currency: 'GTQ',
      }).format(amount);
    },

    formatDate(dateString) {
      if (!dateString) return ''
      return new Date(dateString).toLocaleDateString()
    },

    formatDateTime(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString('en-US', { hour12: false })
    },

    getClientUsername(clientId) {
      const client = this.dcaClients.find(c => c.id === clientId)
      return client ? (client.username || client.user_id.substring(0, 8) + '...') : clientId
    },


    // Configuration Methods
    async getLamassuConfig() {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          '/myextension/api/v1/dca/config',
          this.g.user.wallets[0].inkey
        )
        this.lamassuConfig = data
        
        // When opening config dialog, populate the selected wallets if they exist
        if (data && data.source_wallet_id) {
          const wallet = this.g.user.wallets.find(w => w.id === data.source_wallet_id)
          if (wallet) {
            this.configDialog.data.selectedWallet = wallet
          }
        }
        if (data && data.commission_wallet_id) {
          const commissionWallet = this.g.user.wallets.find(w => w.id === data.commission_wallet_id)
          if (commissionWallet) {
            this.configDialog.data.selectedCommissionWallet = commissionWallet
          }
        }
      } catch (error) {
        // It's OK if no config exists yet
        this.lamassuConfig = null
      }
    },
    
    async saveConfiguration() {
      try {
        const data = {
          host: this.configDialog.data.host,
          port: this.configDialog.data.port,
          database_name: this.configDialog.data.database_name,
          username: this.configDialog.data.username,
          password: this.configDialog.data.password,
          source_wallet_id: this.configDialog.data.selectedWallet?.id,
          commission_wallet_id: this.configDialog.data.selectedCommissionWallet?.id,
          // SSH Tunnel settings
          use_ssh_tunnel: this.configDialog.data.use_ssh_tunnel,
          ssh_host: this.configDialog.data.ssh_host,
          ssh_port: this.configDialog.data.ssh_port,
          ssh_username: this.configDialog.data.ssh_username,
          ssh_password: this.configDialog.data.ssh_password,
          ssh_private_key: this.configDialog.data.ssh_private_key
        }
        
        const {data: config} = await LNbits.api.request(
          'POST',
          '/myextension/api/v1/dca/config',
          this.g.user.wallets[0].adminkey,
          data
        )
        
        this.lamassuConfig = config
        this.closeConfigDialog()
        
        this.$q.notify({
          type: 'positive',
          message: 'Database configuration saved successfully',
          timeout: 5000
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    
    closeConfigDialog() {
      this.configDialog.show = false
      this.configDialog.data = {
        host: '',
        port: 5432,
        database_name: '',
        username: '',
        password: '',
        selectedWallet: null,
        selectedCommissionWallet: null,
        // SSH Tunnel settings
        use_ssh_tunnel: false,
        ssh_host: '',
        ssh_port: 22,
        ssh_username: '',
        ssh_password: '',
        ssh_private_key: ''
      }
    },

    // DCA Client Methods
    async getDcaClients() {
      try {
        const { data } = await LNbits.api.request(
          'GET',
          '/myextension/api/v1/dca/clients',
          this.g.user.wallets[0].inkey
        )
        this.dcaClients = data
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },

    // Test Client Creation (temporary for testing)
    async createTestClient() {
      try {
        const testData = {
          user_id: this.g.user.id,
          wallet_id: this.g.user.wallets[0].id,
          username: this.g.user.username || `user_${this.g.user.id.substring(0, 8)}`,
          dca_mode: 'flow'
        }

        const { data: newClient } = await LNbits.api.request(
          'POST',
          '/myextension/api/v1/dca/clients',
          this.g.user.wallets[0].adminkey,
          testData
        )

        this.dcaClients.push(newClient)

        this.$q.notify({
          type: 'positive',
          message: 'Test client created successfully!',
          timeout: 5000
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },

    // Quick Deposit Methods
    async sendQuickDeposit() {
      try {
        const data = {
          client_id: this.quickDepositForm.selectedClient?.value,
          amount: this.quickDepositForm.amount,
          currency: 'GTQ',
          notes: this.quickDepositForm.notes
        }

        const { data: newDeposit } = await LNbits.api.request(
          'POST',
          '/myextension/api/v1/dca/deposits',
          this.g.user.wallets[0].adminkey,
          data
        )

        this.deposits.unshift(newDeposit)

        // Reset form
        this.quickDepositForm = {
          selectedClient: null,
          amount: null,
          notes: ''
        }

        this.$q.notify({
          type: 'positive',
          message: 'Deposit created successfully',
          timeout: 5000
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },

    async viewClientDetails(client) {
      try {
        const { data: balance } = await LNbits.api.request(
          'GET',
          `/myextension/api/v1/dca/clients/${client.id}/balance`,
          this.g.user.wallets[0].inkey
        )
        this.clientDetailsDialog.data = client
        this.clientDetailsDialog.balance = balance
        this.clientDetailsDialog.show = true
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },

    // Deposit Methods
    async getDeposits() {
      try {
        const { data } = await LNbits.api.request(
          'GET',
          '/myextension/api/v1/dca/deposits',
          this.g.user.wallets[0].inkey
        )
        this.deposits = data
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },

    addDepositDialog(client) {
      this.depositFormDialog.data = {
        client_id: client.id,
        client_name: client.username || `${client.user_id.substring(0, 8)}...`,
        currency: 'GTQ'
      }
      this.depositFormDialog.show = true
    },

    async sendDepositData() {
      try {
        const data = {
          client_id: this.depositFormDialog.data.client_id,
          amount: this.depositFormDialog.data.amount,
          currency: this.depositFormDialog.data.currency,
          notes: this.depositFormDialog.data.notes
        }

        if (this.depositFormDialog.data.id) {
          // Update existing deposit (mainly for notes/status)
          const { data: updatedDeposit } = await LNbits.api.request(
            'PUT',
            `/myextension/api/v1/dca/deposits/${this.depositFormDialog.data.id}`,
            this.g.user.wallets[0].adminkey,
            { status: this.depositFormDialog.data.status, notes: data.notes }
          )
          const index = this.deposits.findIndex(d => d.id === updatedDeposit.id)
          if (index !== -1) {
            this.deposits.splice(index, 1, updatedDeposit)
          }
        } else {
          // Create new deposit
          const { data: newDeposit } = await LNbits.api.request(
            'POST',
            '/myextension/api/v1/dca/deposits',
            this.g.user.wallets[0].adminkey,
            data
          )
          this.deposits.unshift(newDeposit)
        }

        this.closeDepositFormDialog()
        this.$q.notify({
          type: 'positive',
          message: this.depositFormDialog.data.id ? 'Deposit updated successfully' : 'Deposit created successfully',
          timeout: 5000
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },

    closeDepositFormDialog() {
      this.depositFormDialog.show = false
      this.depositFormDialog.data = {
        currency: 'GTQ'
      }
    },

    async confirmDeposit(deposit) {
      try {
        await LNbits.utils
          .confirmDialog('Confirm that this deposit has been physically placed in the ATM machine?')
          .onOk(async () => {
            const { data: updatedDeposit } = await LNbits.api.request(
              'PUT',
              `/myextension/api/v1/dca/deposits/${deposit.id}/status`,
              this.g.user.wallets[0].adminkey,
              { status: 'confirmed', notes: 'Confirmed by admin - money placed in machine' }
            )
            const index = this.deposits.findIndex(d => d.id === deposit.id)
            if (index !== -1) {
              this.deposits.splice(index, 1, updatedDeposit)
            }
            this.$q.notify({
              type: 'positive',
              message: 'Deposit confirmed! DCA is now active for this client.',
              timeout: 5000
            })
          })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },

    editDeposit(deposit) {
      this.depositFormDialog.data = { ...deposit }
      this.depositFormDialog.show = true
    },

    // Export Methods
    async exportClientsCSV() {
      await LNbits.utils.exportCSV(this.clientsTable.columns, this.dcaClients)
    },

    async exportDepositsCSV() {
      await LNbits.utils.exportCSV(this.depositsTable.columns, this.deposits)
    },
    
    // Polling Methods
    async testDatabaseConnection() {
      this.testingConnection = true
      try {
        const {data} = await LNbits.api.request(
          'POST',
          '/myextension/api/v1/dca/test-connection',
          this.g.user.wallets[0].adminkey
        )
        
        // Show detailed results in a dialog
        const stepsList = data.steps ? data.steps.join('\n') : 'No detailed steps available'
        
        let dialogContent = `<strong>Connection Test Results</strong><br/><br/>`
        
        if (data.ssh_tunnel_used) {
          dialogContent += `<strong>SSH Tunnel:</strong> ${data.ssh_tunnel_success ? '✅ Success' : '❌ Failed'}<br/>`
        }
        
        dialogContent += `<strong>Database:</strong> ${data.database_connection_success ? '✅ Success' : '❌ Failed'}<br/><br/>`
        dialogContent += `<strong>Detailed Steps:</strong><br/>`
        dialogContent += stepsList.replace(/\n/g, '<br/>')
        
        this.$q.dialog({
          title: data.success ? 'Connection Test Passed' : 'Connection Test Failed',
          message: dialogContent,
          html: true,
          ok: {
            color: data.success ? 'positive' : 'negative',
            label: 'Close'
          }
        })
        
        // Also show a brief notification
        this.$q.notify({
          type: data.success ? 'positive' : 'negative',
          message: data.message,
          timeout: 3000
        })
        
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      } finally {
        this.testingConnection = false
      }
    },
    
    async manualPoll() {
      this.runningManualPoll = true
      try {
        const {data} = await LNbits.api.request(
          'POST',
          '/myextension/api/v1/dca/manual-poll',
          this.g.user.wallets[0].adminkey
        )
        
        this.lastPollTime = new Date().toLocaleString()
        this.$q.notify({
          type: 'positive',
          message: `Manual poll completed. Found ${data.transactions_processed} new transactions.`,
          timeout: 5000
        })
        
        // Refresh data
        await this.getDeposits()
        await this.getLamassuConfig()
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      } finally {
        this.runningManualPoll = false
      }
    },

    // Legacy Methods (keep for backward compatibility)
    async closeFormDialog() {
      this.formDialog.show = false
      this.formDialog.data = {}
    },
    async getMyExtensions() {
      await LNbits.api
        .request(
          'GET',
          '/myextension/api/v1/myex',
          this.g.user.wallets[0].inkey
        )
        .then(response => {
          this.myex = response.data
        })
        .catch(err => {
          LNbits.utils.notifyApiError(err)
        })
    },
    async sendMyExtensionData() {
      const data = {
        name: this.formDialog.data.name,
        lnurlwithdrawamount: this.formDialog.data.lnurlwithdrawamount,
        lnurlpayamount: this.formDialog.data.lnurlpayamount
      }
      const wallet = _.findWhere(this.g.user.wallets, {
        id: this.formDialog.data.wallet
      })
      if (this.formDialog.data.id) {
        data.id = this.formDialog.data.id
        data.total = this.formDialog.data.total
        await this.updateMyExtension(wallet, data)
      } else {
        await this.createMyExtension(wallet, data)
      }
    },

    async updateMyExtensionForm(tempId) {
      const myextension = _.findWhere(this.myex, { id: tempId })
      this.formDialog.data = {
        ...myextension
      }
      if (this.formDialog.data.tip_wallet != '') {
        this.formDialog.advanced.tips = true
      }
      if (this.formDialog.data.withdrawlimit >= 1) {
        this.formDialog.advanced.otc = true
      }
      this.formDialog.show = true
    },
    async createMyExtension(wallet, data) {
      data.wallet = wallet.id
      await LNbits.api
        .request('POST', '/myextension/api/v1/myex', wallet.adminkey, data)
        .then(response => {
          this.myex.push(response.data)
          this.closeFormDialog()
        })
        .catch(error => {
          LNbits.utils.notifyApiError(error)
        })
    },

    async updateMyExtension(wallet, data) {
      data.wallet = wallet.id
      await LNbits.api
        .request(
          'PUT',
          `/myextension/api/v1/myex/${data.id}`,
          wallet.adminkey,
          data
        )
        .then(response => {
          this.myex = _.reject(this.myex, obj => obj.id == data.id)
          this.myex.push(response.data)
          this.closeFormDialog()
        })
        .catch(error => {
          LNbits.utils.notifyApiError(error)
        })
    },
    async deleteMyExtension(tempId) {
      var myextension = _.findWhere(this.myex, { id: tempId })
      const wallet = _.findWhere(this.g.user.wallets, {
        id: myextension.wallet
      })
      await LNbits.utils
        .confirmDialog('Are you sure you want to delete this MyExtension?')
        .onOk(function () {
          LNbits.api
            .request(
              'DELETE',
              '/myextension/api/v1/myex/' + tempId,
              wallet.adminkey
            )
            .then(() => {
              this.myex = _.reject(this.myex, function (obj) {
                return obj.id === myextension.id
              })
            })
            .catch(error => {
              LNbits.utils.notifyApiError(error)
            })
        })
    },

    async exportCSV() {
      await LNbits.utils.exportCSV(this.myexTable.columns, this.myex)
    },
    async itemsArray(tempId) {
      const myextension = _.findWhere(this.myex, { id: tempId })
      return [...myextension.itemsMap.values()]
    },
    async openformDialog(id) {
      const [tempId, itemId] = id.split(':')
      const myextension = _.findWhere(this.myex, { id: tempId })
      if (itemId) {
        const item = myextension.itemsMap.get(id)
        this.formDialog.data = {
          ...item,
          myextension: tempId
        }
      } else {
        this.formDialog.data.myextension = tempId
      }
      this.formDialog.data.currency = myextension.currency
      this.formDialog.show = true
    },
    async openUrlDialog(tempid) {
      this.urlDialog.data = _.findWhere(this.myex, { id: tempid })
      this.qrValue = this.urlDialog.data.lnurlpay

      // Connecting to our websocket fired in tasks.py
      this.connectWebocket(this.urlDialog.data.id)

      this.urlDialog.show = true
    },
    async closeformDialog() {
      this.formDialog.show = false
      this.formDialog.data = {}
    },
    async createInvoice(tempid) {
      ///////////////////////////////////////////////////
      ///Simple call to the api to create an invoice/////
      ///////////////////////////////////////////////////
      myex = _.findWhere(this.myex, { id: tempid })
      const wallet = _.findWhere(this.g.user.wallets, { id: myex.wallet })
      const data = {
        myextension_id: tempid,
        amount: this.invoiceAmount,
        memo: 'MyExtension - ' + myex.name
      }
      await LNbits.api
        .request('POST', `/myextension/api/v1/myex/payment`, wallet.inkey, data)
        .then(response => {
          this.qrValue = response.data.payment_request
          this.connectWebocket(wallet.inkey)
        })
        .catch(error => {
          LNbits.utils.notifyApiError(error)
        })
    },
    connectWebocket(myextension_id) {
      //////////////////////////////////////////////////
      ///wait for pay action to happen and do a thing////
      ///////////////////////////////////////////////////
      if (location.protocol !== 'http:') {
        localUrl =
          'wss://' +
          document.domain +
          ':' +
          location.port +
          '/api/v1/ws/' +
          myextension_id
      } else {
        localUrl =
          'ws://' +
          document.domain +
          ':' +
          location.port +
          '/api/v1/ws/' +
          myextension_id
      }
      this.connection = new WebSocket(localUrl)
      this.connection.onmessage = () => {
        this.urlDialog.show = false
      }
    }
  },
  ///////////////////////////////////////////////////
  //////LIFECYCLE FUNCTIONS RUNNING ON PAGE LOAD/////
  ///////////////////////////////////////////////////
  async created() {
    // Load DCA admin data
    await Promise.all([
      this.getLamassuConfig(),
      this.getDcaClients(),
      this.getDeposits()
    ])

    // Legacy data loading
    await this.getMyExtensions()
  },

  computed: {
    isConfigFormValid() {
      const data = this.configDialog.data
      
      // Basic database fields are required
      const basicValid = data.host && data.database_name && data.username && data.selectedWallet
      
      // If SSH tunnel is enabled, validate SSH fields
      if (data.use_ssh_tunnel) {
        const sshValid = data.ssh_host && data.ssh_username && 
                        (data.ssh_password || data.ssh_private_key)
        return basicValid && sshValid
      }
      
      return basicValid
    },
    
    clientOptions() {
      return this.dcaClients.map(client => ({
        label: `${client.username || client.user_id.substring(0, 8) + '...'} (${client.dca_mode})`,
        value: client.id
      }))
    },

    totalDcaBalance() {
      return this.deposits
        .filter(d => d.status === 'confirmed')
        .reduce((total, deposit) => total + deposit.amount, 0)
    }
  }
})
