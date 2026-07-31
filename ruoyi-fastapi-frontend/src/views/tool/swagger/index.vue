<template>
   <i-frame v-model:src="url"></i-frame>
</template>

<script setup>
import iFrame from '@/components/iFrame'

// FastAPI exposes the generated OpenAPI UI at /docs. The frontend API prefix
// keeps this request on the configured gateway in each environment.
const url = ref(`${import.meta.env.VITE_APP_BASE_API}/docs`)
</script>
