###
#* @Date: 2021-06-19 11:32:07
#* @LastEditors: Hwrn
#* @LastEditTime: 2021-06-19 11:36:19
#* @filePath: /KEGG/Scripts/demo-pathview.r
#* @Description:
###
#BiocManager::install('pathview')
library(pathview)

KEGG_DIR = '/home/hwrn/Data/Database2/KEGG/pathview'


SAMPLES = c(
    'TY.040',
    'TY.041',
    'TY.044'
)


ko.sample = list()
total.ko = c()

for (i in seq(length(SAMPLES))) {
  method = paste(SAMPLES[i] , '-sickle-megahit', sep = '')
  KO_list = read.table(paste('03_annot/funct/', method, '/',
                             method, '-KO.tsv', sep = ''),
                       header = F, as.is = T)
  uniq_ko = KO_list[!duplicated(KO_list$V2),'V2']
  ko.sample[[i]] = uniq_ko
  total.ko = c(total.ko, uniq_ko)

}
head(total.ko)
total.ko = total.ko[!duplicated(total.ko)]

ko.data = data.frame(row.names = total.ko)
for (i in seq(length(SAMPLES))) {
  method = paste(SAMPLES[i] , '-sickle-megahit', sep = '')
  ko.data[method] = ifelse(total.ko %in% ko.sample[[i]], 1, 0)

}

head(ko.data)

p<-pathview(gene.data = ko.data,
            pathway.id = '00910',
            species = 'ko',
            kegg.native = T,
            kegg.dir = KEGG_DIR,
            out.suffix = 'ko.data')
