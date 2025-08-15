<template>
  <layout-text v-if="example.id">
    <template #header>
      <toolbar-laptop
        :doc-id="example.id"
        :enable-auto-labeling.sync="enableAutoLabeling"
        :guideline-text="project.guideline"
        :is-reviewd="example.isConfirmed"
        :total="totalExample"
        class="d-none d-sm-block"
        @click:clear-label="clear"
        @click:review="confirm"
      >
        <button-label-switch class="ms-2" @change="labelComponent = $event" />
      </toolbar-laptop>
      <toolbar-mobile :total="totalExample" class="d-flex d-sm-none" />
    </template>
    <template #content>
      <v-card v-shortkey="shortKeys" @shortkey="addOrRemoveCategory($event.srcKey)">
        <v-card-title>
          <component
            :is="labelComponent"
            :labels="labels"
            :annotations="categories"
            :single-label="exclusive"
            @add="addCategory"
            @remove="removeCategory"
          />
        </v-card-title>
        <v-divider />
        <v-card-text class="title highlight" style="white-space: pre-wrap" v-text="example.text" />
      </v-card>
    </template>
    <template #sidebar>
      <annotation-progress :progress="progress" />
      <list-metadata :metadata="example.meta" class="mt-4" />
    </template>
  </layout-text>
</template>

<script>
import { mdiChevronDown, mdiChevronUp } from '@mdi/js'
import _ from 'lodash'
import { mapGetters } from 'vuex'
import LayoutText from '@/components/tasks/layout/LayoutText'
import ListMetadata from '@/components/tasks/metadata/ListMetadata'
import AnnotationProgress from '@/components/tasks/sidebar/AnnotationProgress.vue'
import LabelGroup from '@/components/tasks/textClassification/LabelGroup'
import LabelSelect from '@/components/tasks/textClassification/LabelSelect'
import ButtonLabelSwitch from '@/components/tasks/toolbar/buttons/ButtonLabelSwitch'
import ToolbarLaptop from '@/components/tasks/toolbar/ToolbarLaptop'
import ToolbarMobile from '@/components/tasks/toolbar/ToolbarMobile'
import { Category } from '~/domain/models/tasks/category'

export default {
  components: {
    AnnotationProgress,
    ButtonLabelSwitch,
    LabelGroup,
    LabelSelect,
    LayoutText,
    ListMetadata,
    ToolbarLaptop,
    ToolbarMobile
  },

  layout: 'workspace',

  validate({ params, query }) {
    return /^\d+$/.test(params.id) && /^\d+$/.test(query.page)
  },

  data() {
    return {
      example: {},
      totalExample: 0,
      labels: [],
      categories: [],
      project: {},
      enableAutoLabeling: false,
      progress: {},
      selectedLabelIndex: null,
      labelComponent: 'label-group',
      exclusive: true
    }
  },

  async fetch() {
    const response = await this.$services.example.fetchOne(
      this.projectId,
      this.$route.query.page,
      this.$route.query.q,
      this.$route.query.isChecked,
      this.$route.query.ordering
    )
    this.totalExample = response.count
    this.example = response.items[0]

    if (this.enableAutoLabeling && !this.example.isConfirmed) {
      await this.autoLabel(this.example.id)
    }
    await this.listCategory(this.example.id)
  },

  computed: {
    ...mapGetters('auth', ['isAuthenticated', 'getUsername', 'getUserId']),
    ...mapGetters('config', ['isRTL']),

    shortKeys() {
      return Object.fromEntries(this.labels.map((item) => [item.id, [item.suffixKey]]))
    },

    projectId() {
      return this.$route.params.id
    },

    isSingleLabel() {
      return this.project.singleClassClassification
    }
  },

  watch: {
    '$route.query': '$fetch',
    async enableAutoLabeling(val) {
      if (val && !this.example.isConfirmed) {
        await this.autoLabel(this.example.id)
        await this.listCategory(this.example.id)
      }
    }
  },

  async created() {
    this.project = await this.$services.project.findById(this.projectId)
    this.labels = await this.$services.categoryType.list(this.projectId)
    this.progress = await this.$repositories.metrics.fetchMyProgress(this.projectId)
  },

  methods: {
    async listCategory(exampleId) {
      this.categories = await this.$repositories.category.list(this.projectId, exampleId)
    },

    async addCategory(labelId) {
      if (this.exclusive) {
        for (const cat of this.categories) {
          await this.$repositories.category.delete(this.projectId, this.example.id, cat.id)
        }
        this.categories = []
      }
      const category = Category.create(labelId)
      await this.$repositories.category.create(this.projectId, this.example.id, category)
      await this.listCategory(this.example.id)
    },

    async removeCategory(id) {
      await this.$repositories.category.delete(this.projectId, this.example.id, id)
      await this.listCategory(this.example.id)
    },

    async addOrRemoveCategory(key) {
      const labelId = parseInt(key, 10)
      const existing = this.categories.find(cat => cat.label === labelId)
      if (existing) {
        await this.removeCategory(existing.id)
      } else {
        await this.addCategory(labelId)
      }
    },

    async clear() {
      await this.$repositories.category.clear(this.projectId, this.example.id)
      await this.listCategory(this.example.id)
    },

    async autoLabel(exampleId) {
      try {
        await this.$services.category.autoLabel(this.projectId, exampleId)
      } catch (e) {
        console.error(e.response?.data?.detail || e.message)
        this.enableAutoLabeling = false
        alert(e.response?.data?.detail || 'Auto-labeling failed.')
      }
    },

    async updateProgress() {
      this.progress = await this.$repositories.metrics.fetchMyProgress(this.projectId)
    },

    async confirm() {
      await this.$services.example.confirm(this.projectId, this.example.id)
      await this.$fetch()
      this.updateProgress()
    }
  }
}
</script>

<style scoped>
.annotation-text {
  font-size: 1.25rem !important;
  font-weight: 500;
  line-height: 2rem;
  font-family: 'Roboto', sans-serif !important;
  opacity: 0.6;
}
</style>